from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import requests
from skyfield.api import Loader, Star, wgs84
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
    for (hip, row), x_value, y_value in zip(
        visible_stars.iterrows(), x, y, strict=True
    ):
        magnitude = float(row["magnitude"])
        radius = max(0.7, 3.4 - 0.42 * magnitude)
        star_marks.append(_circle(float(x_value), float(y_value), radius, "star"))

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
                _circle(float(object_x), float(object_y), 5.0, "solar-system"),
                (
                    f'<text class="object-label" x="{float(object_x) + 8:.1f}" '
                    f'y="{float(object_y) - 7:.1f}">{escape(name)}</text>'
                ),
            )
        )

    local_label = moment.strftime("%d %B %Y, %I:%M %p").replace(" 0", " ")
    title = f"Sky above {site_name}, {local_label} local"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-labelledby="title description">
  <title id="title">{escape(title)}</title>
  <desc id="description">All-sky finder chart with north at top and east at left.</desc>
  <style>
    :root {{ color-scheme: light dark; }}
    .background {{ fill: #f4efe5; }} .horizon {{ fill: none; stroke: #706a5e; stroke-width: 2; }}
    .altitude {{ fill: none; stroke: #b9b1a2; stroke-width: 1; stroke-dasharray: 3 6; }}
    .constellation {{ stroke: #8d9980; stroke-width: 1.4; opacity: .75; }}
    .star {{ fill: #28251f; }} .solar-system {{ fill: #ad503d; stroke: #f4efe5; stroke-width: 2; }}
    text {{ fill: #4d4941; font-family: Atkinson Hyperlegible, system-ui, sans-serif; }}
    .direction {{ font-size: 20px; font-weight: 700; }} .constellation-label {{ font-size: 11px; opacity: .7; }}
    .object-label {{ fill: #8d3425; font-size: 14px; font-weight: 700; }}
    @media (prefers-color-scheme: dark) {{
      .background {{ fill: #171814; }} .horizon {{ stroke: #aaa79b; }} .altitude {{ stroke: #4c5048; }}
      .constellation {{ stroke: #7d9173; }} .star {{ fill: #eee8db; }}
      .solar-system {{ fill: #e27d62; stroke: #171814; }} text {{ fill: #d8d2c4; }}
      .object-label {{ fill: #f09a83; }}
    }}
    @media print {{ .background {{ fill: white; }} .star {{ fill: black; }} }}
  </style>
  <rect class="background" width="800" height="800"/>
  <circle class="altitude" cx="400" cy="400" r="110"/><circle class="altitude" cx="400" cy="400" r="220"/>
  <circle class="horizon" cx="400" cy="400" r="330"/>
  {''.join(segments)}{''.join(star_marks)}{''.join(constellation_labels)}{''.join(object_marks)}
  <text class="direction" x="400" y="48" text-anchor="middle">N</text>
  <text class="direction" x="48" y="407" text-anchor="middle">E</text>
  <text class="direction" x="400" y="770" text-anchor="middle">S</text>
  <text class="direction" x="752" y="407" text-anchor="middle">W</text>
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
