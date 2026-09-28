from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from skyfield.api import Loader, Star, wgs84
from skyfield.data import hipparcos

from paa.sources.occult_import import score_occultation

LUNAR_RADIUS_KM = 1737.4
COARSE_STEP_MINUTES = 120
COARSE_SEARCH_RADIUS_DEG = 0.95
REFINE_STEP_MINUTES = 2
REFINE_HALF_WINDOW_HOURS = 3

HIP_NAMES = {
    21421: "Aldebaran",
    49669: "Regulus",
    65474: "Spica",
    80763: "Antares",
}

PLANETS = {
    "Mercury": ("mercury barycenter", 2439.7),
    "Venus": ("venus barycenter", 6051.8),
    "Mars": ("mars barycenter", 3389.5),
    "Jupiter": ("jupiter barycenter", 69911.0),
    "Saturn": ("saturn barycenter", 58232.0),
    "Uranus": ("uranus barycenter", 25362.0),
    "Neptune": ("neptune barycenter", 24622.0),
}


def _datetime_grid(start: datetime, stop: datetime, step_minutes: int) -> list[datetime]:
    count = int((stop - start).total_seconds() // (step_minutes * 60)) + 1
    return [start + timedelta(minutes=step_minutes * index) for index in range(count)]


def _group_nearby_indexes(indexes: list[int], max_gap: int = 1) -> list[list[int]]:
    if not indexes:
        return []
    groups = [[indexes[0]]]
    for index in indexes[1:]:
        if index - groups[-1][-1] <= max_gap:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _contact_brackets(
    datetimes: list[datetime], values: np.ndarray
) -> tuple[tuple[datetime, datetime], tuple[datetime, datetime]] | None:
    inside = np.flatnonzero(values <= 0.0)
    if not len(inside):
        return None
    first = int(inside[0])
    last = int(inside[-1])
    if first == 0 or last >= len(datetimes) - 1:
        return None
    return (datetimes[first - 1], datetimes[first]), (
        datetimes[last],
        datetimes[last + 1],
    )


def _bisect_contact(
    left: datetime,
    right: datetime,
    value_at: Callable[[datetime], float],
    iterations: int = 12,
) -> datetime:
    left_value = value_at(left)
    for _ in range(iterations):
        middle = left + (right - left) / 2
        middle_value = value_at(middle)
        if (left_value <= 0) == (middle_value <= 0):
            left = middle
            left_value = middle_value
        else:
            right = middle
    return left + (right - left) / 2


def _ecliptic_band(dataframe, max_magnitude: float):
    ra = np.radians(dataframe.ra_degrees.to_numpy())
    dec = np.radians(dataframe.dec_degrees.to_numpy())
    obliquity = np.radians(23.43928)
    beta = np.arcsin(
        np.sin(dec) * np.cos(obliquity)
        - np.cos(dec) * np.sin(obliquity) * np.sin(ra)
    )
    mask = (
        (dataframe.magnitude.to_numpy() <= max_magnitude)
        & (np.abs(beta) <= np.radians(8.0))
        & np.isfinite(ra)
        & np.isfinite(dec)
    )
    return dataframe[mask]


def _candidate_star_passes(moon_vectors: np.ndarray, star_vectors: np.ndarray) -> dict[int, list[int]]:
    threshold = np.cos(np.radians(COARSE_SEARCH_RADIUS_DEG))
    candidates: dict[int, list[int]] = defaultdict(list)
    chunk_size = 256
    for start in range(0, len(moon_vectors), chunk_size):
        dots = moon_vectors[start : start + chunk_size] @ star_vectors.T
        moon_indexes, star_indexes = np.nonzero(dots >= threshold)
        for moon_index, star_index in zip(moon_indexes, star_indexes, strict=True):
            candidates[int(star_index)].append(start + int(moon_index))
    return candidates


def _normalised_vectors(position) -> np.ndarray:
    vectors = np.asarray(position.position.au).T
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _target_value(observer, moon, target, ts, target_radius_km: float = 0.0):
    def values(datetimes: list[datetime] | datetime) -> np.ndarray | float:
        scalar = isinstance(datetimes, datetime)
        requested = [datetimes] if scalar else datetimes
        times = ts.from_datetimes(requested)
        observer_at = observer.at(times)
        moon_position = observer_at.observe(moon).apparent()
        target_position = observer_at.observe(target).apparent()
        separation = target_position.separation_from(moon_position).radians
        moon_radius = np.arcsin(LUNAR_RADIUS_KM / moon_position.distance().km)
        target_radius = (
            np.arcsin(target_radius_km / target_position.distance().km)
            if target_radius_km
            else 0.0
        )
        result = separation - moon_radius - target_radius
        return float(result[0]) if scalar else result

    return values


def _event_rows(
    *,
    target_name: str,
    target_magnitude: float | None,
    is_planetary: bool,
    coarse_time: datetime,
    observer,
    moon,
    sun,
    target,
    ts,
    timezone_name: str,
    cfg: dict,
    target_radius_km: float = 0.0,
) -> list[dict]:
    start = coarse_time - timedelta(hours=REFINE_HALF_WINDOW_HOURS)
    stop = coarse_time + timedelta(hours=REFINE_HALF_WINDOW_HOURS)
    grid = _datetime_grid(start, stop, REFINE_STEP_MINUTES)
    value_at = _target_value(observer, moon, target, ts, target_radius_km)
    brackets = _contact_brackets(grid, np.asarray(value_at(grid)))
    if brackets is None:
        return []

    ingress = _bisect_contact(*brackets[0], value_at)
    egress = _bisect_contact(*brackets[1], value_at)
    timezone = ZoneInfo(timezone_name)
    rows: list[dict] = []
    for contact, event_type, limb in (
        (ingress, "Geometric disappearance", "leading limb"),
        (egress, "Geometric reappearance", "trailing limb"),
    ):
        time = ts.from_datetime(contact)
        observer_at = observer.at(time)
        moon_position = observer_at.observe(moon).apparent()
        moon_altitude = float(moon_position.altaz()[0].degrees)
        if moon_altitude < float(cfg.get("min_moon_altitude_deg", 10)):
            continue
        sun_altitude = float(observer_at.observe(sun).apparent().altaz()[0].degrees)
        if not is_planetary and sun_altitude > float(cfg.get("max_sun_altitude_deg", -6)):
            continue
        local = contact.astimezone(timezone)
        row = {
            "datetime_local": local.isoformat(),
            "target": target_name,
            "target_mag": target_magnitude,
            "moon_altitude_deg": round(moon_altitude, 2),
            "limb": limb,
            "event_type": event_type,
            "is_planetary": is_planetary,
        }
        row["score"] = score_occultation(row, cfg)
        rows.append(row)
    return rows


def compute_lunar_occultations(
    *,
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    cfg: dict,
    source_cache: Path,
) -> list[dict]:
    source_cache.mkdir(parents=True, exist_ok=True)
    loader = Loader(str(source_cache))
    ephemeris = loader(str(cfg.get("ephemeris", "de440s.bsp")))
    timescale = loader.timescale()
    with loader.open(hipparcos.URL) as handle:
        catalogue = hipparcos.load_dataframe(handle)
    stars = _ecliptic_band(catalogue, float(cfg.get("catalog_max_mag", 9.0)))

    observer = ephemeris["earth"] + wgs84.latlon(
        latitude_deg, longitude_deg, elevation_m=elevation_m
    )
    moon = ephemeris["moon"]
    sun = ephemeris["sun"]
    start = datetime(year, 1, 1, tzinfo=UTC)
    stop = datetime(year + 1, 1, 1, tzinfo=UTC)
    coarse_datetimes = _datetime_grid(start, stop, COARSE_STEP_MINUTES)
    coarse_times = timescale.from_datetimes(coarse_datetimes)
    moon_vectors = _normalised_vectors(
        observer.at(coarse_times).observe(moon).apparent()
    )

    midyear = timescale.utc(year, 7, 1)
    star_positions = observer.at(midyear).observe(Star.from_dataframe(stars)).apparent()
    star_vectors = _normalised_vectors(star_positions)
    candidates = _candidate_star_passes(moon_vectors, star_vectors)

    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for star_index, indexes in candidates.items():
        hip_id = int(stars.index[star_index])
        star_row = stars.iloc[star_index]
        target = Star.from_dataframe(star_row)
        target_name = HIP_NAMES.get(hip_id, f"HIP {hip_id}")
        for group in _group_nearby_indexes(sorted(set(indexes))):
            coarse_index = min(
                group,
                key=lambda index: np.linalg.norm(
                    moon_vectors[index] - star_vectors[star_index]
                ),
            )
            event_rows = _event_rows(
                target_name=target_name,
                target_magnitude=float(star_row.magnitude),
                is_planetary=False,
                coarse_time=coarse_datetimes[coarse_index],
                observer=observer,
                moon=moon,
                sun=sun,
                target=target,
                ts=timescale,
                timezone_name=timezone_name,
                cfg=cfg,
            )
            for row in event_rows:
                key = (row["target"], row["event_type"], row["datetime_local"][:16])
                if key not in seen:
                    rows.append(row)
                    seen.add(key)

    for name, (ephemeris_name, radius_km) in PLANETS.items():
        target = ephemeris[ephemeris_name]
        target_vectors = _normalised_vectors(
            observer.at(coarse_times).observe(target).apparent()
        )
        dots = np.sum(moon_vectors * target_vectors, axis=1)
        indexes = np.flatnonzero(dots >= np.cos(np.radians(2.0))).tolist()
        for group in _group_nearby_indexes(indexes):
            coarse_index = max(group, key=lambda index: dots[index])
            rows.extend(
                _event_rows(
                    target_name=name,
                    target_magnitude=None,
                    is_planetary=True,
                    coarse_time=coarse_datetimes[coarse_index],
                    observer=observer,
                    moon=moon,
                    sun=sun,
                    target=target,
                    ts=timescale,
                    timezone_name=timezone_name,
                    cfg=cfg,
                    target_radius_km=radius_km,
                )
            )

    rows = [
        row
        for row in rows
        if datetime.fromisoformat(row["datetime_local"]).year == year
    ]
    rows.sort(key=lambda row: (row["datetime_local"], row["target"], row["event_type"]))
    return rows
