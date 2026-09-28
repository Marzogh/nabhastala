from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import acos, pi
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from skyfield import almanac, eclipselib
from skyfield.api import Loader, wgs84
from skyfield.framelib import ecliptic_frame

SUN_RADIUS_KM = 695700.0
MOON_RADIUS_KM = 1737.4

PLANETS = {
    "Mercury": "mercury barycenter",
    "Venus": "venus barycenter",
    "Mars": "mars barycenter",
    "Jupiter": "jupiter barycenter",
    "Saturn": "saturn barycenter",
    "Uranus": "uranus barycenter",
    "Neptune": "neptune barycenter",
}


def circle_overlap_fraction(radius: float, occulter_radius: float, separation: float) -> float:
    """Return the fraction of the first circle covered by the second."""
    if separation >= radius + occulter_radius:
        return 0.0
    if separation <= abs(radius - occulter_radius):
        covered_radius = min(radius, occulter_radius)
        return min(1.0, (covered_radius / radius) ** 2)
    first_cosine = (separation**2 + radius**2 - occulter_radius**2) / (
        2 * separation * radius
    )
    second_cosine = (separation**2 + occulter_radius**2 - radius**2) / (
        2 * separation * occulter_radius
    )
    first = radius**2 * acos(max(-1.0, min(1.0, first_cosine)))
    second = occulter_radius**2 * acos(max(-1.0, min(1.0, second_cosine)))
    triangle = 0.5 * (
        (-separation + radius + occulter_radius)
        * (separation + radius - occulter_radius)
        * (separation - radius + occulter_radius)
        * (separation + radius + occulter_radius)
    ) ** 0.5
    return (first + second - triangle) / (pi * radius**2)


def _row(
    moment,
    timezone: ZoneInfo,
    *,
    category: str,
    target: str,
    event: str,
    value: str,
    visibility: str,
    altitude_deg: float | None,
    details: str,
) -> dict:
    return {
        "datetime_local": moment.utc_datetime().astimezone(timezone).isoformat(),
        "category": category,
        "target": target,
        "event": event,
        "value": value,
        "visibility": visibility,
        "altitude_deg": "" if altitude_deg is None else round(altitude_deg, 2),
        "details": details,
    }


def _solar_eclipses(
    year: int, ephemeris, timescale, observer, timezone: ZoneInfo
) -> list[dict]:
    start = timescale.utc(year, 1, 1)
    stop = timescale.utc(year + 1, 1, 1)
    moments, phases = almanac.find_discrete(start, stop, almanac.moon_phases(ephemeris))
    sun = ephemeris["sun"]
    moon = ephemeris["moon"]
    rows: list[dict] = []
    for moment, phase in zip(moments, phases, strict=True):
        if int(phase) != 0:
            continue
        centre = moment.utc_datetime().replace(tzinfo=UTC)
        datetimes = [centre + timedelta(minutes=minute) for minute in range(-240, 241)]
        times = timescale.from_datetimes(datetimes)
        observer_at = observer.at(times)
        sun_position = observer_at.observe(sun).apparent()
        moon_position = observer_at.observe(moon).apparent()
        separation = sun_position.separation_from(moon_position).radians
        sun_radius = np.arcsin(SUN_RADIUS_KM / sun_position.distance().km)
        moon_radius = np.arcsin(MOON_RADIUS_KM / moon_position.distance().km)
        index = int(np.argmin(separation - sun_radius - moon_radius))
        if separation[index] >= sun_radius[index] + moon_radius[index]:
            continue
        maximum = times[index]
        sun_altitude = float(sun_position.altaz()[0].degrees[index])
        fraction = circle_overlap_fraction(
            float(sun_radius[index]), float(moon_radius[index]), float(separation[index])
        )
        central = separation[index] <= abs(moon_radius[index] - sun_radius[index])
        if central and moon_radius[index] >= sun_radius[index]:
            event = "Total solar eclipse"
        elif central:
            event = "Annular solar eclipse"
        else:
            event = "Partial solar eclipse"
        visibility = "Visible" if sun_altitude > -0.833 else "Below horizon"
        rows.append(
            _row(
                maximum,
                timezone,
                category="Eclipse",
                target="Sun",
                event=event,
                value=f"{fraction:.0%} obscuration",
                visibility=visibility,
                altitude_deg=sun_altitude,
                details="Maximum local geometric obscuration.",
            )
        )
    return rows


def _lunar_eclipses(
    year: int, ephemeris, timescale, observer, timezone: ZoneInfo
) -> list[dict]:
    start = timescale.utc(year, 1, 1)
    stop = timescale.utc(year + 1, 1, 1)
    moments, kinds, details = eclipselib.lunar_eclipses(start, stop, ephemeris)
    moon = ephemeris["moon"]
    rows: list[dict] = []
    for index, (moment, kind) in enumerate(zip(moments, kinds, strict=True)):
        altitude = float(observer.at(moment).observe(moon).apparent().altaz()[0].degrees)
        event = f"{eclipselib.LUNAR_ECLIPSES[int(kind)]} lunar eclipse"
        visibility = "Visible at maximum" if altitude > 0 else "Below horizon at maximum"
        rows.append(
            _row(
                moment,
                timezone,
                category="Eclipse",
                target="Moon",
                event=event,
                value=f"umbral magnitude {float(details['umbral_magnitude'][index]):.2f}",
                visibility=visibility,
                altitude_deg=altitude,
                details="Greatest eclipse; visibility refers to the observing horizon.",
            )
        )
    return rows


def _planetary_phenomena(year: int, ephemeris, timescale, timezone: ZoneInfo) -> list[dict]:
    datetimes = [
        datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=day)
        for day in range((datetime(year + 1, 1, 2, tzinfo=UTC) - datetime(year, 1, 1, tzinfo=UTC)).days)
    ]
    times = timescale.from_datetimes(datetimes)
    earth_at = ephemeris["earth"].at(times)
    sun_position = earth_at.observe(ephemeris["sun"]).apparent()
    sun_longitude = sun_position.frame_latlon(ecliptic_frame)[1].radians
    rows: list[dict] = []

    for name in ("Mercury", "Venus"):
        position = earth_at.observe(ephemeris[PLANETS[name]]).apparent()
        separation = position.separation_from(sun_position).degrees
        longitude = position.frame_latlon(ecliptic_frame)[1].radians
        for index in range(1, len(separation) - 1):
            if not (
                separation[index] > separation[index - 1] >= 0
                and separation[index] >= separation[index + 1]
            ):
                continue
            moment = times[index]
            signed = (longitude[index] - sun_longitude[index] + pi) % (2 * pi) - pi
            direction = "Eastern" if signed > 0 else "Western"
            rows.append(
                _row(
                    moment,
                    timezone,
                    category="Planetary phenomena",
                    target=name,
                    event=f"Greatest {direction.lower()} elongation",
                    value=f"{float(separation[index]):.1f}°",
                    visibility="Evening sky" if direction == "Eastern" else "Morning sky",
                    altitude_deg=None,
                    details=f"{direction} of the Sun.",
                )
            )

    for name, ephemeris_name in PLANETS.items():
        position = earth_at.observe(ephemeris[ephemeris_name]).apparent()
        longitude = np.unwrap(position.frame_latlon(ecliptic_frame)[1].radians)
        rate = np.gradient(longitude)
        for index in range(1, len(rate)):
            if (
                rate[index - 1] == 0
                or rate[index] == 0
                or np.sign(rate[index - 1]) == np.sign(rate[index])
            ):
                continue
            moment = times[index]
            direction = (
                "Direct to retrograde" if rate[index - 1] > 0 else "Retrograde to direct"
            )
            rows.append(
                _row(
                    moment,
                    timezone,
                    category="Planetary phenomena",
                    target=name,
                    event="Stationary point",
                    value=direction,
                    visibility="Date applies worldwide",
                    altitude_deg=None,
                    details="Apparent motion changes direction.",
                )
            )

    start = timescale.utc(year, 1, 1)
    stop = timescale.utc(year + 1, 1, 1)
    for name in ("Mars", "Jupiter", "Saturn", "Uranus", "Neptune"):
        moments, states = almanac.find_discrete(
            start,
            stop,
            almanac.oppositions_conjunctions(ephemeris, ephemeris[PLANETS[name]]),
        )
        for moment, state in zip(moments, states, strict=True):
            if int(state) != 1:
                continue
            rows.append(
                _row(
                    moment,
                    timezone,
                    category="Planetary phenomena",
                    target=name,
                    event="Opposition",
                    value="180° solar elongation",
                    visibility="Best annual placement",
                    altitude_deg=None,
                    details="The planet is opposite the Sun and visible for most of the night.",
                )
            )
    return rows


def compute_astronomical_phenomena(
    *,
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    source_cache: Path,
    ephemeris_name: str = "de440s.bsp",
) -> list[dict]:
    source_cache.mkdir(parents=True, exist_ok=True)
    loader = Loader(str(source_cache))
    ephemeris = loader(ephemeris_name)
    timescale = loader.timescale()
    observer = ephemeris["earth"] + wgs84.latlon(
        latitude_deg, longitude_deg, elevation_m=elevation_m
    )
    timezone = ZoneInfo(timezone_name)
    rows = [
        *_solar_eclipses(year, ephemeris, timescale, observer, timezone),
        *_lunar_eclipses(year, ephemeris, timescale, observer, timezone),
        *_planetary_phenomena(year, ephemeris, timescale, timezone),
    ]
    rows.sort(key=lambda row: (row["datetime_local"], row["target"], row["event"]))
    return rows
