from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import requests
from skyfield.api import Loader, Star, load_constellation_names, wgs84
from skyfield.data import hipparcos

CONSTELLATION_URL = (
    "https://raw.githubusercontent.com/astronoray/constellation_figures/"
    "main/constellationship.fab"
)

PLANETS = {
    "Mercury": "mercury barycenter",
    "Venus": "venus barycenter",
    "Mars": "mars barycenter",
    "Jupiter": "jupiter barycenter",
    "Saturn": "saturn barycenter",
    "Uranus": "uranus barycenter",
    "Neptune": "neptune barycenter",
}

BRIGHT_STAR_NAMES = {
    7588: "Achernar",
    21421: "Aldebaran",
    24436: "Rigel",
    24608: "Capella",
    27989: "Betelgeuse",
    30438: "Canopus",
    32349: "Sirius",
    37279: "Procyon",
    37826: "Pollux",
    49669: "Regulus",
    60718: "Acrux",
    62434: "Mimosa",
    65474: "Spica",
    68702: "Hadar",
    69673: "Arcturus",
    71683: "Alpha Centauri",
    80763: "Antares",
    91262: "Vega",
    97649: "Altair",
    102098: "Deneb",
    113368: "Fomalhaut",
}


def project_altaz(
    altitude_deg: np.ndarray | float,
    azimuth_deg: np.ndarray | float,
    *,
    centre: float = 400.0,
    radius: float = 330.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Project horizontal coordinates with north up and east left."""
    altitude = np.asarray(altitude_deg, dtype=float)
    azimuth = np.radians(np.asarray(azimuth_deg, dtype=float))
    distance = (90.0 - altitude) / 90.0 * radius
    return centre - distance * np.sin(azimuth), centre - distance * np.cos(azimuth)


def _constellation_lines(path: Path) -> dict[str, tuple[tuple[int, int], ...]]:
    result: dict[str, tuple[tuple[int, int], ...]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.split()
        if len(parts) < 4 or parts[0].startswith("#"):
            continue
        abbreviation = parts[0]
        pair_count = int(parts[1])
        values = [int(value) for value in parts[2 : 2 + pair_count * 2]]
        result[abbreviation] = tuple(zip(values[::2], values[1::2], strict=True))
    return result


def _ensure_constellations(source_cache: Path) -> Path:
    path = source_cache / "constellationship.fab"
    if path.exists():
        return path
    source_cache.mkdir(parents=True, exist_ok=True)
    response = requests.get(CONSTELLATION_URL, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def _load_stars(source_root: Path):
    hip_path = source_root / "occultations" / "hip_main.dat"
    if not hip_path.exists():
        raise FileNotFoundError(
            "Hipparcos catalogue is missing; run the occultation build once before rendering."
        )
    with hip_path.open("rb") as handle:
        stars = hipparcos.load_dataframe(handle)
    stars = stars[
        (stars["magnitude"] <= 6.5)
        & stars["ra_degrees"].notna()
        & stars["dec_degrees"].notna()
    ].copy()
    stars[["parallax_mas", "ra_mas_per_year", "dec_mas_per_year"]] = stars[
        ["parallax_mas", "ra_mas_per_year", "dec_mas_per_year"]
    ].fillna(0.0)
    return stars


def _circle(x: float, y: float, radius: float, css_class: str) -> str:
    return f'<circle class="{css_class}" cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}"/>'


def _compass_ring() -> str:
    marks: list[str] = []
    for bearing in range(0, 360, 5):
        angle = np.radians(bearing)
        inner_radius = 313 if bearing % 30 == 0 else 318 if bearing % 10 == 0 else 324
        x1 = 400 - inner_radius * np.sin(angle)
        y1 = 400 - inner_radius * np.cos(angle)
        x2 = 400 - 330 * np.sin(angle)
        y2 = 400 - 330 * np.cos(angle)
        marks.append(
            f'<line class="bearing-tick" x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}"/>'
        )
        if bearing % 30 == 0:
            label_x = 400 - 301 * np.sin(angle)
            label_y = 404 - 301 * np.cos(angle)
            marks.append(
                f'<text class="bearing-label" x="{label_x:.1f}" '
                f'y="{label_y:.1f}" text-anchor="middle">{bearing}°</text>'
            )
    for bearing, label in zip(
        range(0, 360, 45), ("N", "NE", "E", "SE", "S", "SW", "W", "NW"), strict=True
    ):
        angle = np.radians(bearing)
        label_x = 400 - 361 * np.sin(angle)
        label_y = 407 - 361 * np.cos(angle)
        marks.append(
            f'<text class="direction" x="{label_x:.1f}" y="{label_y:.1f}" '
            f'text-anchor="middle">{label}</text>'
        )
    return "".join(marks)


def _render_svg(
    *,
    moment: datetime,
    site_name: str,
    observer,
    ephemeris,
    timescale,
    stars,
    lines: dict[str, tuple[tuple[int, int], ...]],
) -> str:
    time = timescale.from_datetime(moment)
    star_positions = observer.at(time).observe(Star.from_dataframe(stars)).apparent()
    altitude, azimuth, _ = star_positions.altaz()
    visible = altitude.degrees >= 0
    visible_stars = stars.loc[visible].copy()
    x, y = project_altaz(altitude.degrees[visible], azimuth.degrees[visible])
    positions = {
        int(hip): (float(x_value), float(y_value))
        for hip, x_value, y_value in zip(visible_stars.index, x, y, strict=True)
    }

    segments: list[str] = []
    constellation_labels: list[str] = []
    for abbreviation, pairs in lines.items():
        points: list[tuple[float, float]] = []
        for first, second in pairs:
            if first not in positions or second not in positions:
                continue
            x1, y1 = positions[first]
            x2, y2 = positions[second]
            if (x2 - x1) ** 2 + (y2 - y1) ** 2 > 280**2:
                continue
            segments.append(
                f'<line class="constellation" x1="{x1:.1f}" y1="{y1:.1f}" '
                f'x2="{x2:.1f}" y2="{y2:.1f}"/>'
            )
            points.extend(((x1, y1), (x2, y2)))
        if len(points) >= 4:
            label_x = sum(point[0] for point in points) / len(points)
            label_y = sum(point[1] for point in points) / len(points)
            constellation_labels.append(
                f'<text class="constellation-label" x="{label_x:.1f}" '
                f'y="{label_y:.1f}">{escape(abbreviation)}</text>'
            )

    star_marks: list[str] = []
    constellation_hips = {
        hip
        for pairs in lines.values()
        for pair in pairs
        for hip in pair
    }
    for (hip, row), x_value, y_value in zip(
        visible_stars.iterrows(), x, y, strict=True
    ):
        magnitude = float(row["magnitude"])
        radius = max(0.7, 3.4 - 0.42 * magnitude)
        css_class = "star constellation-star" if int(hip) in constellation_hips else "star"
        star_marks.append(_circle(float(x_value), float(y_value), radius, css_class))

    object_marks: list[str] = []
    for name, key in {**PLANETS, "Moon": "moon"}.items():
        position = observer.at(time).observe(ephemeris[key]).apparent()
        object_altitude, object_azimuth, _ = position.altaz()
        if object_altitude.degrees < 0:
            continue
        object_x, object_y = project_altaz(
            object_altitude.degrees, object_azimuth.degrees
        )
        object_marks.extend(
            (
                _circle(
                    float(object_x),
                    float(object_y),
                    6.5 if name == "Moon" else 5.0,
                    f"solar-system body-{name.lower()}",
                ),
                (
                    f'<text class="object-label label-{name.lower()}" '
                    f'x="{float(object_x) + 8:.1f}" '
                    f'y="{float(object_y) - 7:.1f}">{escape(name)}</text>'
                ),
            )
        )

    local_label = moment.strftime("%d %B %Y, %I:%M %p").replace(" 0", " ")
    title = f"Sky above {site_name}, {local_label} local"
    compass_ring = _compass_ring()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-labelledby="title description">
  <title id="title">{escape(title)}</title>
  <desc id="description">All-sky finder chart with north at top and east at left.</desc>
  <style>
    :root {{ color-scheme: light dark; }}
    .background {{ fill: #f4efe5; }} .horizon {{ fill: none; stroke: #706a5e; stroke-width: 2; }}
    .altitude {{ fill: none; stroke: #b9b1a2; stroke-width: 1; stroke-dasharray: 3 6; }}
    .constellation {{ stroke: #8d9980; stroke-width: 1.4; opacity: .75; }}
    .star {{ fill: #3e3a34; }} .constellation-star {{ fill: #536047; }}
    .solar-system {{ stroke: #f4efe5; stroke-width: 2; }}
    .body-moon {{ fill: #756f65; }} .body-mercury {{ fill: #69645d; }} .body-venus {{ fill: #a96c15; }}
    .body-mars {{ fill: #b13b2a; }} .body-jupiter {{ fill: #96633d; }} .body-saturn {{ fill: #88702e; }}
    .body-uranus {{ fill: #277f83; }} .body-neptune {{ fill: #365f9d; }}
    text {{ fill: #4d4941; font-family: Atkinson Hyperlegible, system-ui, sans-serif; }}
    .bearing-tick {{ stroke: #706a5e; stroke-width: 1; }}
    .direction {{ font-size: 17px; font-weight: 700; }} .bearing-label {{ font-size: 9px; opacity: .75; }}
    .constellation-label {{ font-size: 11px; opacity: .7; }}
    .object-label {{ font-size: 14px; font-weight: 700; }}
    .label-moon {{ fill: #625d55; }} .label-mercury {{ fill: #5a5650; }} .label-venus {{ fill: #8b5810; }}
    .label-mars {{ fill: #9d3022; }} .label-jupiter {{ fill: #7b4e2e; }} .label-saturn {{ fill: #705b22; }}
    .label-uranus {{ fill: #1f7074; }} .label-neptune {{ fill: #2d538e; }}
    @media (prefers-color-scheme: dark) {{
      .background {{ fill: #171814; }} .horizon {{ stroke: #aaa79b; }} .altitude {{ stroke: #4c5048; }}
      .constellation {{ stroke: #7d9173; }} .star {{ fill: #e8e2d7; }} .constellation-star {{ fill: #a8bc8c; }}
      .solar-system {{ stroke: #171814; }} text {{ fill: #d8d2c4; }}
      .body-moon {{ fill: #e3ded0; }} .body-mercury {{ fill: #b7afa1; }} .body-venus {{ fill: #f0c27a; }}
      .body-mars {{ fill: #f0785f; }} .body-jupiter {{ fill: #d7a46d; }} .body-saturn {{ fill: #d9bd75; }}
      .body-uranus {{ fill: #71c5c9; }} .body-neptune {{ fill: #648fd8; }}
      .label-moon {{ fill: #e3ded0; }} .label-mercury {{ fill: #b7afa1; }} .label-venus {{ fill: #f0c27a; }}
      .label-mars {{ fill: #f0785f; }} .label-jupiter {{ fill: #d7a46d; }} .label-saturn {{ fill: #d9bd75; }}
      .label-uranus {{ fill: #71c5c9; }} .label-neptune {{ fill: #648fd8; }}
    }}
    @media print {{
      .background {{ fill: white; }} .star, .constellation-star {{ fill: black; }}
      .constellation {{ stroke: #666; }} .solar-system {{ stroke: black; stroke-width: 2; }}
      .body-moon {{ fill: white; }} .body-mercury, .body-venus, .body-mars, .body-jupiter,
      .body-saturn, .body-uranus, .body-neptune {{ fill: black; }}
      .object-label {{ fill: black; }}
    }}
  </style>
  <rect class="background" width="800" height="800"/>
  <circle class="altitude" cx="400" cy="400" r="110"/><circle class="altitude" cx="400" cy="400" r="220"/>
  <circle class="horizon" cx="400" cy="400" r="330"/>
  {compass_ring}
  {''.join(segments)}{''.join(star_marks)}{''.join(constellation_labels)}{''.join(object_marks)}
</svg>'''


def generate_monthly_sky_charts(
    *,
    year: int,
    site_name: str,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    destination: Path,
    source_root: Path,
    ephemeris_name: str = "de440s.bsp",
) -> tuple[Path, ...]:
    """Generate twelve deterministic all-sky SVG charts for one edition."""
    stars = _load_stars(source_root)
    lines = _constellation_lines(_ensure_constellations(source_root / "sky"))
    loader = Loader(str(source_root / "occultations"))
    ephemeris = loader(ephemeris_name)
    timescale = loader.timescale()
    observer = ephemeris["earth"] + wgs84.latlon(
        latitude_deg, longitude_deg, elevation_m=elevation_m
    )
    timezone = ZoneInfo(timezone_name)
    destination.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for month in range(1, 13):
        moment = datetime(year, month, 15, 22, 0, tzinfo=timezone)
        output = destination / f"month-{month:02d}.svg"
        output.write_text(
            _render_svg(
                moment=moment,
                site_name=site_name,
                observer=observer,
                ephemeris=ephemeris,
                timescale=timescale,
                stars=stars,
                lines=lines,
            ),
            encoding="utf-8",
        )
        outputs.append(output)
    return tuple(outputs)


def generate_placeholder_sky_charts(
    *, year: int, destination: Path
) -> tuple[Path, ...]:
    """Keep fixture and partial renders navigable when catalogues are absent."""
    destination.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for month in range(1, 13):
        output = destination / f"month-{month:02d}.svg"
        output.write_text(
            f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-labelledby="title">
  <title id="title">Sky chart unavailable for {year}-{month:02d}</title>
  <rect width="800" height="800" fill="#f4efe5"/>
  <circle cx="400" cy="400" r="330" fill="none" stroke="#706a5e" stroke-width="2"/>
  <text x="400" y="400" text-anchor="middle" fill="#4d4941" font-family="sans-serif">Sky chart unavailable</text>
</svg>''',
            encoding="utf-8",
        )
        outputs.append(output)
    return tuple(outputs)


def generate_interactive_sky_data(
    *,
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    destination: Path,
    source_root: Path,
    ephemeris_name: str = "de440s.bsp",
) -> Path:
    """Build a compact annual catalogue for browser-side sky projection."""
    stars = _load_stars(source_root)
    constellation_lines = _constellation_lines(
        _ensure_constellations(source_root / "sky")
    )
    constellation_names = dict(load_constellation_names())
    loader = Loader(str(source_root / "occultations"))
    ephemeris = loader(ephemeris_name)
    timescale = loader.timescale()
    observer = ephemeris["earth"] + wgs84.latlon(
        latitude_deg, longitude_deg, elevation_m=elevation_m
    )

    start = datetime(year, 1, 1, tzinfo=UTC)
    stop = datetime(year + 1, 1, 1, tzinfo=UTC)
    datetimes: list[datetime] = []
    moment = start
    while moment <= stop:
        datetimes.append(moment)
        moment += timedelta(hours=3)
    times = timescale.from_datetimes(datetimes)

    bodies: dict[str, list[list[float]]] = {}
    for name, key in {
        "Sun": "sun",
        "Moon": "moon",
        **PLANETS,
    }.items():
        right_ascension, declination, _ = (
            observer.at(times).observe(ephemeris[key]).apparent().radec()
        )
        bodies[name] = [
            [round(float(ra), 5), round(float(dec), 5)]
            for ra, dec in zip(
                right_ascension.hours * 15.0,
                declination.degrees,
                strict=True,
            )
        ]

    star_rows = [
        [
            int(hip),
            round(float(row["ra_degrees"]), 5),
            round(float(row["dec_degrees"]), 5),
            round(float(row["magnitude"]), 2),
            BRIGHT_STAR_NAMES.get(int(hip), ""),
        ]
        for hip, row in stars.iterrows()
    ]
    constellations = [
        [
            abbreviation,
            constellation_names.get(abbreviation, abbreviation),
            [[first, second] for first, second in pairs],
        ]
        for abbreviation, pairs in constellation_lines.items()
    ]
    payload = {
        "year": year,
        "latitude": latitude_deg,
        "longitude": longitude_deg,
        "elevation_m": elevation_m,
        "timezone": timezone_name,
        "ephemeris_start_utc": start.isoformat(),
        "ephemeris_step_hours": 3,
        "stars": star_rows,
        "constellations": constellations,
        "bodies": bodies,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return destination
