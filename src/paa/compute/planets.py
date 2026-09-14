from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def _imports():
    try:
        from astropy import units as u  # type: ignore
        from astropy.coordinates import AltAz, EarthLocation, get_body, get_sun  # type: ignore
        from astropy.time import Time  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Planet visibility requires astropy. Install dependencies first.") from exc
    return u, AltAz, EarthLocation, get_body, get_sun, Time


PLANETS = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]


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


def compute_planet_visibility(
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone: str,
    min_alt_deg: float,
    excellent_alt_deg: float,
) -> tuple[list[dict], list[dict]]:
    u, AltAz, EarthLocation, get_body, get_sun, Time = _imports()
    loc = EarthLocation(lat=latitude_deg * u.deg, lon=longitude_deg * u.deg, height=elevation_m * u.m)
    tz = ZoneInfo(timezone)

    daily_rows: list[dict] = []
    monthly_best: dict[tuple[str, str], dict] = {}

    d = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    step = timedelta(minutes=30)

    while d < end:
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
            best_idx = int(altitudes.argmax())
            best_alt = float(altitudes[best_idx])
            best_time = times[best_idx]
            elong = float(body[best_idx].separation(sun[best_idx]).deg)
            sun_alts = sun.transform_to(altaz_frame).alt.deg

            # Practical inner-planet imaging window in twilight:
            # Sun altitude roughly between -12 and -4 degrees.
            tw_indices = [i for i, sa in enumerate(sun_alts) if -12.0 <= float(sa) <= -4.0]
            tw_best_alt: float | None = None
            tw_best_time: datetime | None = None
            if tw_indices:
                tw_best_idx = max(tw_indices, key=lambda i: float(altitudes[i]))
                tw_best_alt = float(altitudes[tw_best_idx])
                tw_best_time = times[tw_best_idx]

            rating = _rating(best_alt, excellent_alt_deg, min_alt_deg)
            row = {
                "date": d.isoformat(),
                "planet": planet.capitalize(),
                "best_time_local": best_time.isoformat(),
                "max_altitude_deg": round(best_alt, 2),
                "solar_elong_deg": round(elong, 2),
                "twilight_best_time_local": tw_best_time.isoformat() if tw_best_time else "",
                "twilight_max_altitude_deg": round(tw_best_alt, 2) if tw_best_alt is not None else "",
                "visibility_rating": rating,
            }
            daily_rows.append(row)

            month = d.strftime("%Y-%m")
            key = (month, planet)
            current = monthly_best.get(key)
            if current is None or best_alt > float(current["best_altitude_deg"]):
                monthly_best[key] = {
                    "month": month,
                    "planet": planet.capitalize(),
                    "best_date": d.isoformat(),
                    "best_altitude_deg": round(best_alt, 2),
                    "rating": rating,
                }

        d += timedelta(days=1)

    monthly_rows = [monthly_best[k] for k in sorted(monthly_best.keys())]
    return daily_rows, monthly_rows
