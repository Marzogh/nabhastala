from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from time import perf_counter
from zoneinfo import ZoneInfo


def _imports():
    try:
        from astropy import units as u  # type: ignore
        from astropy.coordinates import AltAz, EarthLocation, get_body, get_sun  # type: ignore
        from astropy.time import Time  # type: ignore
        from astropy.utils import iers  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Planet visibility requires astropy. Install dependencies first."
        ) from exc
    iers.conf.auto_download = False
    iers.conf.auto_max_age = None
    return u, AltAz, EarthLocation, get_body, get_sun, Time


PLANETS = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]
OBSERVABLE_SUN_ALTITUDE_DEG = -4.0


def _rating(max_alt: float, excellent_alt: float, min_alt: float) -> str:
    if max_alt >= excellent_alt:
        return "excellent"
    if max_alt >= min_alt:
        return "good"
    if max_alt >= min_alt - 10:
        return "fair"
    if max_alt > 0:
        return "poor"
    return "not visible"


def _observation_period(value: datetime) -> str:
    hour = value.hour
    if 16 <= hour < 22:
        return "evening"
    if hour >= 22 or hour < 3:
        return "overnight"
    return "predawn"


def _best_observable_index(
    altitudes: Sequence[float],
    sun_altitudes: Sequence[float],
    *,
    sun_limit_deg: float = OBSERVABLE_SUN_ALTITUDE_DEG,
) -> int | None:
    """Return the highest target sample while the Sun is below the observing limit."""
    candidates = [
        index
        for index, sun_altitude in enumerate(sun_altitudes)
        if float(sun_altitude) <= sun_limit_deg
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda index: float(altitudes[index]))


def compute_planet_visibility(
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone: str,
    min_alt_deg: float,
    excellent_alt_deg: float,
    ephemeris_rows: list[dict] | None = None,
    progress: Callable[[str], None] = print,
) -> tuple[list[dict], list[dict]]:
    u, AltAz, EarthLocation, get_body, get_sun, Time = _imports()
    loc = EarthLocation(
        lat=latitude_deg * u.deg, lon=longitude_deg * u.deg, height=elevation_m * u.m
    )
    tz = ZoneInfo(timezone)

    daily_rows: list[dict] = []
    monthly_best: dict[tuple[str, str], dict] = {}
    transits = {
        (str(row.get("local_date", "")), str(row.get("object_id", ""))): row
        for row in (ephemeris_rows or [])
        if row.get("object_class") == "planet" and row.get("event_type") == "upper_transit"
    }

    d = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    step = timedelta(minutes=30)
    started = perf_counter()
    active_month = ""

    while d < end:
        month = d.strftime("%Y-%m")
        if month != active_month:
            active_month = month
            progress(
                f"[planets] {active_month}: start; elapsed {perf_counter() - started:.1f}s"
            )
        day_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
        times = []
        t = day_start
        while t < day_start + timedelta(days=1):
            times.append(t)
            t += step
        time_arr = Time(times)
        altaz_frame = AltAz(obstime=time_arr, location=loc)
        sun = get_sun(time_arr)

        for planet in PLANETS:
            body = get_body(planet, time_arr)
            altaz = body.transform_to(altaz_frame)
            altitudes = altaz.alt.deg
            sun_alts = sun.transform_to(altaz_frame).alt.deg
            all_day_idx = int(altitudes.argmax())
            transit = transits.get((d.isoformat(), planet))
            observable_idx = _best_observable_index(altitudes, sun_alts)
            if observable_idx is None:
                best_alt = -90.0
                best_time = None
                elong = float(body[all_day_idx].separation(sun[all_day_idx]).deg)
                sun_alt = None
                period = "unavailable"
            else:
                best_alt = float(altitudes[observable_idx])
                best_time = times[observable_idx]
                elong = float(body[observable_idx].separation(sun[observable_idx]).deg)
                sun_alt = float(sun_alts[observable_idx])
                period = _observation_period(best_time)

            rating = _rating(best_alt, excellent_alt_deg, min_alt_deg)
            row = {
                "date": d.isoformat(),
                "planet": planet.capitalize(),
                "best_time_local": best_time.isoformat() if best_time else "",
                "max_altitude_deg": round(best_alt, 2),
                "solar_elong_deg": round(elong, 2),
                "twilight_best_time_local": best_time.isoformat() if best_time else "",
                "twilight_max_altitude_deg": round(best_alt, 2) if best_time else "",
                "visibility_rating": rating,
                "observation_period": period,
                "sun_altitude_deg": round(sun_alt, 2) if sun_alt is not None else "",
                "all_day_best_time_local": (
                    str(transit["event_time_local"])
                    if transit is not None
                    else times[all_day_idx].isoformat()
                ),
                "all_day_max_altitude_deg": (
                    round(float(transit["altitude_deg"]), 2)
                    if transit is not None
                    else round(float(altitudes[all_day_idx]), 2)
                ),
            }
            daily_rows.append(row)

            key = (month, planet)
            current = monthly_best.get(key)
            if current is None or best_alt > float(current["best_altitude_deg"]):
                monthly_best[key] = {
                    "month": month,
                    "planet": planet.capitalize(),
                    "best_date": d.isoformat(),
                    "best_altitude_deg": round(best_alt, 2),
                    "rating": rating,
                    "best_time_local": best_time.isoformat() if best_time else "",
                    "observation_period": period,
                    "solar_elong_deg": round(elong, 2),
                }

        d += timedelta(days=1)

    monthly_rows = [monthly_best[k] for k in sorted(monthly_best.keys())]
    progress(
        f"[planets] complete; {len(daily_rows)} daily rows in "
        f"{perf_counter() - started:.1f}s"
    )
    return daily_rows, monthly_rows
