from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

import requests

from paa.models import Site

SUN_HORIZON_DEG = -0.8333
MOON_HORIZON_DEG = -0.8392
POINT_HORIZON_DEG = -0.5667
PLANETS = {
    "mercury": "mercury barycenter",
    "venus": "venus barycenter",
    "mars": "mars barycenter",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
}
CALCULATION_BASIS = "Skyfield DE440s; standard apparent astronomical horizon"
ENGINE_VERSION = "2"
MAX_EVENT_SEARCH_STEP_DAYS = 1 / 48
SOURCE_URLS = {
    "de440s.bsp": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp",
    "hip_main.dat": "https://cdsarc.cds.unistra.fr/ftp/cats/I/239/hip_main.dat",
}


def _imports():
    try:
        from skyfield import almanac  # type: ignore
        from skyfield.api import Star, load, load_file, wgs84  # type: ignore
        from skyfield.data import hipparcos  # type: ignore
        from skyfield.named_stars import named_star_dict  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Ephemeris generation requires Skyfield") from exc
    return almanac, Star, load, load_file, wgs84, hipparcos, named_star_dict


def source_paths(source_root: Path, ephemeris_name: str = "de440s.bsp") -> tuple[Path, Path]:
    occultations = source_root / "occultations"
    return occultations / ephemeris_name, occultations / "hip_main.dat"


def require_sources(source_root: Path, ephemeris_name: str = "de440s.bsp") -> tuple[Path, Path]:
    ephemeris, stars = source_paths(source_root, ephemeris_name)
    missing = [str(path) for path in (ephemeris, stars) if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Missing cached ephemeris source(s): "
            + ", ".join(missing)
            + ". Run the printed astro-almanac fetch command before the annual build."
        )
    return ephemeris, stars


def fetch_sources(
    source_root: Path,
    ephemeris_name: str = "de440s.bsp",
    progress: Callable[[str], None] = print,
) -> tuple[Path, Path]:
    destination_dir = source_root / "occultations"
    destination_dir.mkdir(parents=True, exist_ok=True)
    requested = (
        (destination_dir / ephemeris_name, SOURCE_URLS.get(ephemeris_name)),
        (destination_dir / "hip_main.dat", SOURCE_URLS["hip_main.dat"]),
    )
    for destination, url in requested:
        if destination.is_file():
            progress(
                f"[fetch] {destination.name}: cached; "
                f"{destination.stat().st_size / 1024 / 1024:.1f} MiB"
            )
            continue
        if not url:
            raise RuntimeError(
                f"No download URL is configured for ephemeris file {ephemeris_name}"
            )
        partial = destination.with_name(destination.name + ".part")
        progress(f"[fetch] {destination.name}: downloading {url}")
        response = requests.get(url, stream=True, timeout=120)
        try:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            report_every = max(total // 20, 5 * 1024 * 1024)
            written = 0
            next_report = report_every
            with partial.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    written += len(chunk)
                    if written >= next_report:
                        if total:
                            progress(
                                f"[fetch] {destination.name}: "
                                f"{written / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MiB"
                            )
                        else:
                            progress(
                                f"[fetch] {destination.name}: "
                                f"{written / 1024 / 1024:.1f} MiB"
                            )
                        next_report += report_every
        finally:
            response.close()
        partial.replace(destination)
        progress(
            f"[fetch] {destination.name}: complete; "
            f"{destination.stat().st_size / 1024 / 1024:.1f} MiB"
        )
    return require_sources(source_root, ephemeris_name)


def source_fingerprint(source_root: Path, ephemeris_name: str = "de440s.bsp") -> str:
    digest = hashlib.sha256()
    for path in require_sources(source_root, ephemeris_name):
        digest.update(path.name.encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _rounded_datetime(value: datetime) -> datetime:
    if value.microsecond >= 500_000:
        value = value.replace(microsecond=0) + timedelta(seconds=1)
    return value.replace(microsecond=0)


def _stellar_search_step_days(
    latitude_deg: float,
    declination_deg: float,
    horizon_deg: float,
) -> float:
    """Choose a step that cannot skip a star's shorter horizon interval."""
    latitude = math.radians(latitude_deg)
    declination = math.radians(declination_deg)
    horizon = math.radians(horizon_deg)
    denominator = math.cos(latitude) * math.cos(declination)
    if abs(denominator) < 1e-12:
        return MAX_EVENT_SEARCH_STEP_DAYS
    crossing = (
        math.sin(horizon) - math.sin(latitude) * math.sin(declination)
    ) / denominator
    if crossing <= -1 or crossing >= 1:
        return MAX_EVENT_SEARCH_STEP_DAYS
    hour_angle = math.acos(crossing)
    fraction_above = hour_angle / math.pi
    shorter_interval_days = min(fraction_above, 1 - fraction_above) * 0.9972695663
    return min(MAX_EVENT_SEARCH_STEP_DAYS, shorter_interval_days / 4)


def _event_row(
    *,
    moment,
    observer,
    target,
    timezone: ZoneInfo,
    object_class: str,
    object_id: str,
    object_name: str,
    magnitude: float | None,
    event_type: str,
    horizon_state: str,
) -> dict[str, object]:
    utc = _rounded_datetime(moment.utc_datetime().replace(tzinfo=UTC))
    local = utc.astimezone(timezone)
    altitude, azimuth, _ = observer.at(moment).observe(target).apparent().altaz()
    return {
        "local_date": local.date().isoformat(),
        "object_class": object_class,
        "object_id": object_id,
        "object_name": object_name,
        "magnitude": "" if magnitude is None else round(magnitude, 2),
        "event_type": event_type,
        "event_time_utc": utc.isoformat(),
        "event_time_local": local.isoformat(),
        "azimuth_deg": round(float(azimuth.degrees), 3),
        "altitude_deg": round(float(altitude.degrees), 3),
        "horizon_state": horizon_state,
        "calculation_basis": CALCULATION_BASIS,
    }


def _body_events(
    *,
    almanac,
    ephemeris,
    topos,
    target,
    start,
    stop,
    timezone: ZoneInfo,
    object_class: str,
    object_id: str,
    object_name: str,
    horizon_degrees: float,
    magnitude: float | None = None,
    search_step_days: float = MAX_EVENT_SEARCH_STEP_DAYS,
) -> list[dict[str, object]]:
    observer = ephemeris["earth"] + topos
    up_function = almanac.risings_and_settings(
        ephemeris, target, topos, horizon_degrees=horizon_degrees
    )
    up_function.step_days = search_step_days
    rise_times, rise_kinds = almanac.find_discrete(start, stop, up_function)
    state = "normal"
    if not len(rise_times):
        state = "always_above" if bool(up_function(start)) else "always_below"
    rows: list[dict[str, object]] = []
    for moment, kind in zip(rise_times, rise_kinds, strict=True):
        rows.append(
            _event_row(
                moment=moment,
                observer=observer,
                target=target,
                timezone=timezone,
                object_class=object_class,
                object_id=object_id,
                object_name=object_name,
                magnitude=magnitude,
                event_type="rise" if int(kind) else "set",
                horizon_state=state,
            )
        )
    transit_times, transit_kinds = almanac.find_discrete(
        start, stop, almanac.meridian_transits(ephemeris, target, topos)
    )
    for moment, kind in zip(transit_times, transit_kinds, strict=True):
        if not int(kind):
            continue
        rows.append(
            _event_row(
                moment=moment,
                observer=observer,
                target=target,
                timezone=timezone,
                object_class=object_class,
                object_id=object_id,
                object_name=object_name,
                magnitude=magnitude,
                event_type="upper_transit",
                horizon_state=state,
            )
        )
    return rows


def compute_daily_ephemeris(
    *,
    year: int,
    site: Site,
    source_root: Path,
    ephemeris_name: str = "de440s.bsp",
    star_magnitude_limit: float = 3.0,
    sun_horizon_deg: float = SUN_HORIZON_DEG,
    moon_horizon_deg: float = MOON_HORIZON_DEG,
    point_horizon_deg: float = POINT_HORIZON_DEG,
    progress: Callable[[str], None] = print,
) -> list[dict[str, object]]:
    almanac, Star, load, load_file, wgs84, hipparcos, named_star_dict = _imports()
    ephemeris_path, star_path = require_sources(source_root, ephemeris_name)
    started = perf_counter()
    progress(f"[ephemeris] {site.id}: loading cached DE440s and Hipparcos sources")
    ephemeris = load_file(str(ephemeris_path))
    timescale = load.timescale()
    timezone = ZoneInfo(site.timezone)
    start = timescale.from_datetime(
        datetime(year, 1, 1, tzinfo=timezone).astimezone(UTC)
    )
    stop = timescale.from_datetime(
        datetime(year + 1, 1, 1, tzinfo=timezone).astimezone(UTC)
    )
    topos = wgs84.latlon(
        site.latitude_deg, site.longitude_deg, elevation_m=site.elevation_m
    )
    rows: list[dict[str, object]] = []

    progress(f"[ephemeris] {site.id}: Sun, Moon and planets")
    rows.extend(
        _body_events(
            almanac=almanac,
            ephemeris=ephemeris,
            topos=topos,
            target=ephemeris["moon"],
            start=start,
            stop=stop,
            timezone=timezone,
            object_class="moon",
            object_id="moon",
            object_name="Moon",
            horizon_degrees=moon_horizon_deg,
        )
    )
    for planet, target_key in PLANETS.items():
        rows.extend(
            _body_events(
                almanac=almanac,
                ephemeris=ephemeris,
                topos=topos,
                target=ephemeris[target_key],
                start=start,
                stop=stop,
                timezone=timezone,
                object_class="planet",
                object_id=planet,
                object_name=planet.capitalize(),
                horizon_degrees=point_horizon_deg,
            )
        )

    sun_rows = _body_events(
        almanac=almanac,
        ephemeris=ephemeris,
        topos=topos,
        target=ephemeris["sun"],
        start=start,
        stop=stop,
        timezone=timezone,
        object_class="sun",
        object_id="sun",
        object_name="Sun",
        horizon_degrees=sun_horizon_deg,
    )
    for row in sun_rows:
        if row["event_type"] == "rise":
            row["event_type"] = "sunrise"
        elif row["event_type"] == "set":
            row["event_type"] = "sunset"
    rows.extend(sun_rows)

    observer = ephemeris["earth"] + topos
    twilight_function = almanac.dark_twilight_day(ephemeris, topos)
    twilight_times, twilight_states = almanac.find_discrete(start, stop, twilight_function)
    previous = int(twilight_function(start))
    labels = {
        (0, 1): "astronomical_dawn",
        (1, 2): "nautical_dawn",
        (2, 3): "civil_dawn",
        (3, 2): "civil_dusk",
        (2, 1): "nautical_dusk",
        (1, 0): "astronomical_dusk",
    }
    for moment, current_value in zip(twilight_times, twilight_states, strict=True):
        current = int(current_value)
        event_type = labels.get((previous, current))
        if event_type:
            rows.append(
                _event_row(
                    moment=moment,
                    observer=observer,
                    target=ephemeris["sun"],
                    timezone=timezone,
                    object_class="sun",
                    object_id="sun",
                    object_name="Sun",
                    magnitude=None,
                    event_type=event_type,
                    horizon_state="normal",
                )
            )
        previous = current
    with star_path.open("rb") as handle:
        catalogue = hipparcos.load_dataframe(handle)
    stars = catalogue[
        (catalogue["magnitude"] <= star_magnitude_limit)
        & catalogue["ra_degrees"].notna()
        & catalogue["dec_degrees"].notna()
    ].sort_index()
    if star_magnitude_limit == 3.0 and len(stars) != 177:
        raise RuntimeError(f"Expected 177 magnitude-3 Hipparcos stars, found {len(stars)}")
    names: dict[int, str] = {}
    for name, hip in named_star_dict.items():
        names.setdefault(int(hip), name)
    total = len(stars)
    progress(f"[ephemeris] {site.id}: stellar events 0/{total}")
    for number, (hip, star_row) in enumerate(stars.iterrows(), 1):
        hip_id = int(hip)
        rows.extend(
            _body_events(
                almanac=almanac,
                ephemeris=ephemeris,
                topos=topos,
                target=Star.from_dataframe(star_row),
                start=start,
                stop=stop,
                timezone=timezone,
                object_class="star",
                object_id=f"HIP {hip_id}",
                object_name=names.get(hip_id, f"HIP {hip_id}"),
                magnitude=float(star_row["magnitude"]),
                horizon_degrees=point_horizon_deg,
                search_step_days=_stellar_search_step_days(
                    site.latitude_deg,
                    float(star_row["dec_degrees"]),
                    point_horizon_deg,
                ),
            )
        )
        if number % 10 == 0 or number == total:
            progress(
                f"[ephemeris] {site.id}: stellar events {number}/{total}; "
                f"elapsed {perf_counter() - started:.1f}s"
            )
    rows.sort(key=lambda row: (str(row["event_time_utc"]), str(row["object_id"])))
    progress(
        f"[ephemeris] {site.id}: complete; {len(rows)} events in "
        f"{perf_counter() - started:.1f}s"
    )
    return rows


def write_deterministic_gzip(csv_path: Path, gzip_path: Path) -> Path:
    gzip_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        csv_path.open("rb") as source,
        gzip_path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as destination,
    ):
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            destination.write(chunk)
    return gzip_path


def validate_ephemeris_rows(
    rows: Iterable[dict[str, object]],
    *,
    expected_star_count: int | None = 177,
    expected_year: int | None = None,
    sun_horizon_deg: float = SUN_HORIZON_DEG,
    moon_horizon_deg: float = MOON_HORIZON_DEG,
    point_horizon_deg: float = POINT_HORIZON_DEG,
) -> list[str]:
    rows = list(rows)
    failures: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    star_ids: set[str] = set()
    star_states: dict[str, set[str]] = {}
    star_events: dict[str, dict[str, list[datetime]]] = {}
    previous_utc: datetime | None = None
    valid_states = {"normal", "always_above", "always_below"}
    threshold_events = {"rise", "set", "sunrise", "sunset"}

    for index, row in enumerate(rows, 1):
        try:
            utc = datetime.fromisoformat(str(row["event_time_utc"]))
            local = datetime.fromisoformat(str(row["event_time_local"]))
        except (KeyError, ValueError) as error:
            failures.append(f"row {index} has an invalid timestamp: {error}")
            continue
        if utc.tzinfo is None or local.tzinfo is None:
            failures.append(f"row {index} timestamp is not offset-aware")
        elif utc.astimezone(UTC) != local.astimezone(UTC):
            failures.append(f"row {index} UTC and local timestamps differ")
        if str(row.get("local_date", "")) != local.date().isoformat():
            failures.append(f"row {index} local_date does not match event_time_local")
        if expected_year is not None and local.year != expected_year:
            failures.append(f"row {index} falls outside local year {expected_year}")
        if previous_utc is not None and utc < previous_utc:
            failures.append(f"row {index} is out of chronological order")
        previous_utc = utc

        object_id = str(row.get("object_id", ""))
        event_type = str(row.get("event_type", ""))
        key = (object_id, event_type, utc.isoformat())
        if key in seen:
            failures.append(f"duplicate event {object_id} {event_type} {utc.isoformat()}")
        seen.add(key)
        if row.get("object_class") == "star":
            star_ids.add(object_id)
            star_states.setdefault(object_id, set()).add(
                str(row.get("horizon_state", ""))
            )
            star_events.setdefault(object_id, {}).setdefault(event_type, []).append(utc)
        if row.get("horizon_state") not in valid_states:
            failures.append(f"row {index} has invalid horizon_state")

        if event_type in threshold_events:
            object_class = str(row.get("object_class", ""))
            expected = (
                sun_horizon_deg
                if object_class == "sun"
                else moon_horizon_deg
                if object_class == "moon"
                else point_horizon_deg
            )
            if abs(float(row["altitude_deg"]) - expected) > 0.05:
                failures.append(
                    f"row {index} {object_id} {event_type} altitude is outside threshold tolerance"
                )

    if expected_star_count is not None and len(star_ids) != expected_star_count:
        failures.append(
            f"expected {expected_star_count} stellar identifiers, found {len(star_ids)}"
        )
    if expected_year is not None:
        for object_id in sorted(star_ids):
            if star_states.get(object_id) != {"normal"}:
                continue
            events = star_events.get(object_id, {})
            for event_type in ("rise", "set"):
                moments = sorted(events.get(event_type, []))
                if len(moments) < 360:
                    failures.append(
                        f"{object_id} has only {len(moments)} {event_type} events in {expected_year}"
                    )
                    continue
                gaps = [
                    later - earlier for earlier, later in pairwise(moments)
                ]
                if gaps and max(gaps) > timedelta(hours=26):
                    failures.append(
                        f"{object_id} has a gap longer than 26 hours between {event_type} events"
                    )
    if not rows:
        failures.append("no ephemeris rows")
    return failures


def compact_sky_events(
    rows: Iterable[dict[str, str]], year: int, timezone: str | None = None
) -> dict[str, object]:
    epoch = datetime(year, 1, 1, tzinfo=UTC)
    type_codes = {
        name: index
        for index, name in enumerate(
            ("rise", "upper_transit", "set", "sunrise", "sunset", "civil_dawn", "civil_dusk", "nautical_dawn", "nautical_dusk", "astronomical_dawn", "astronomical_dusk")
        )
    }
    objects: dict[str, dict[str, object]] = {}
    for row in rows:
        event_type = row.get("event_type", "")
        if event_type not in type_codes:
            continue
        object_id = row["object_id"]
        item = objects.setdefault(
            object_id,
            {
                "name": row.get("object_name") or object_id,
                "class": row.get("object_class", ""),
                "magnitude": row.get("magnitude", ""),
                "state": row.get("horizon_state", "normal"),
                "events": [],
            },
        )
        moment = datetime.fromisoformat(row["event_time_utc"])
        minute = round((moment - epoch).total_seconds() / 60)
        events = item["events"]
        assert isinstance(events, list)
        events.append(
            [
                type_codes[event_type],
                minute,
                round(float(row["azimuth_deg"]), 1),
                round(float(row["altitude_deg"]), 1),
            ]
        )
    return {
        "year": year,
        "timezone": timezone or "UTC",
        "event_types": type_codes,
        "objects": objects,
    }


def write_compact_sky_events(
    csv_path: Path, destination: Path, year: int, timezone: str
) -> Path:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        payload = compact_sky_events(csv.DictReader(handle), year, timezone)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return destination
