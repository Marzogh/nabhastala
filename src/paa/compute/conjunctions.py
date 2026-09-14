from __future__ import annotations

from datetime import date, datetime, timedelta
from itertools import combinations
from math import cos, pi
from zoneinfo import ZoneInfo

PLANETS = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]


def _imports():
    try:
        from astropy import units as u  # type: ignore
        from astropy.coordinates import AltAz, EarthLocation, get_body  # type: ignore
        from astropy.time import Time  # type: ignore
        from astral.moon import phase  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Conjunction computation requires astropy and astral") from exc
    return u, AltAz, EarthLocation, get_body, Time, phase


def _illum_from_phase_index(phase_index: float) -> float:
    angle = (phase_index / 29.53058867) * 2 * pi
    return (1 - cos(angle)) / 2


def _rating(event_type: str, sep_deg: float, alt1: float, alt2: float, sun_alt: float) -> tuple[int, str]:
    if event_type == "sun_planet_conjunction":
        return 0, "not_observable"
    if event_type == "solar_transit":
        return (9, "excellent") if sun_alt > 0 else (2, "fair")

    score = 0
    if sep_deg <= 0.5:
        score += 4
    elif sep_deg <= 1.0:
        score += 3
    elif sep_deg <= 2.0:
        score += 2
    else:
        score += 1

    min_alt = min(alt1, alt2)
    if min_alt >= 30:
        score += 3
    elif min_alt >= 20:
        score += 2
    elif min_alt >= 10:
        score += 1

    if sun_alt <= -12:
        score += 2
    elif sun_alt <= -6:
        score += 1

    if score >= 8:
        return score, "excellent"
    if score >= 6:
        return score, "good"
    if score >= 4:
        return score, "fair"
    return score, "poor"


def _pick_idx(sep, alt_a, alt_b, sun_alt, event_type: str) -> int | None:
    usable = []
    if event_type in {"planet_planet_conjunction", "moon_planet_conjunction"}:
        for i, (aa, bb, sa) in enumerate(zip(alt_a, alt_b, sun_alt, strict=True)):
            if min(float(aa), float(bb)) >= 0 and float(sa) <= -4:
                usable.append(i)
    else:
        usable = list(range(len(sep)))

    if not usable:
        return None
    return min(usable, key=lambda i: float(sep[i]))


def _event_row(
    *,
    day: date,
    idx: int,
    times_local: list[datetime],
    event_type: str,
    body_a: str,
    body_b: str,
    sep_deg: float,
    alt_a: float,
    alt_b: float,
    sun_alt: float,
    elong_deg: float,
    moon_illum: float,
) -> dict:
    transit_flag = False
    if event_type == "sun_planet_conjunction" and body_a in {"mercury", "venus"} and sep_deg <= 0.27:
        event_type = "solar_transit"
        transit_flag = True

    score, rating = _rating(event_type, sep_deg, alt_a, alt_b, sun_alt)
    return {
        "date_local": day.isoformat(),
        "event_type": event_type,
        "primary_body": body_a.capitalize() if body_a != "moon" else "Moon",
        "secondary_body": body_b.capitalize() if body_b != "moon" else "Moon",
        "separation_deg": round(float(sep_deg), 3),
        "event_time_local": times_local[idx].isoformat(),
        "alt_primary_deg": round(float(alt_a), 2),
        "alt_secondary_deg": round(float(alt_b), 2),
        "sun_altitude_deg": round(float(sun_alt), 2),
        "solar_elong_deg": round(float(elong_deg), 3),
        "moon_illumination_fraction": round(float(moon_illum), 3),
        "visibility_rating": rating,
        "score": int(score),
        "is_solar_transit": bool(transit_flag),
        "safety_note": "Use approved solar filters for any near-Sun observing." if event_type in {"sun_planet_conjunction", "solar_transit"} else "",
    }


def compute_conjunctions(
    year: int,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone: str,
) -> list[dict]:
    u, AltAz, EarthLocation, get_body, Time, moon_phase = _imports()
    tz = ZoneInfo(timezone)
    loc = EarthLocation(lat=latitude_deg * u.deg, lon=longitude_deg * u.deg, height=elevation_m * u.m)

    rows: list[dict] = []
    d = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    step = timedelta(minutes=30)

    while d < end:
        day_start = datetime(d.year, d.month, d.day, 0, 0, tzinfo=tz)
        times_local = []
        t = day_start
        while t < day_start + timedelta(days=1):
            times_local.append(t)
            t += step

        t_arr = Time(times_local)
        frame = AltAz(obstime=t_arr, location=loc)

        bodies = {name: get_body(name, t_arr) for name in ["sun", "moon", *PLANETS]}
        alts = {name: bodies[name].transform_to(frame).alt.deg for name in bodies}
        moon_illum = _illum_from_phase_index(float(moon_phase(d)))

        for pa, pb in combinations(PLANETS, 2):
            sep = bodies[pa].separation(bodies[pb]).deg
            idx = _pick_idx(sep, alts[pa], alts[pb], alts["sun"], "planet_planet_conjunction")
            if idx is None:
                continue
            if float(sep[idx]) > 2.0:
                continue
            rows.append(
                _event_row(
                    day=d,
                    idx=idx,
                    times_local=times_local,
                    event_type="planet_planet_conjunction",
                    body_a=pa,
                    body_b=pb,
                    sep_deg=float(sep[idx]),
                    alt_a=float(alts[pa][idx]),
                    alt_b=float(alts[pb][idx]),
                    sun_alt=float(alts["sun"][idx]),
                    elong_deg=float(bodies["sun"][idx].separation(bodies[pa][idx]).deg),
                    moon_illum=moon_illum,
                )
            )

        for p in PLANETS:
            sep = bodies["moon"].separation(bodies[p]).deg
            idx = _pick_idx(sep, alts["moon"], alts[p], alts["sun"], "moon_planet_conjunction")
            if idx is None:
                continue
            if float(sep[idx]) > 5.0:
                continue
            rows.append(
                _event_row(
                    day=d,
                    idx=idx,
                    times_local=times_local,
                    event_type="moon_planet_conjunction",
                    body_a="moon",
                    body_b=p,
                    sep_deg=float(sep[idx]),
                    alt_a=float(alts["moon"][idx]),
                    alt_b=float(alts[p][idx]),
                    sun_alt=float(alts["sun"][idx]),
                    elong_deg=float(bodies["sun"][idx].separation(bodies["moon"][idx]).deg),
                    moon_illum=moon_illum,
                )
            )

        for p in PLANETS:
            sep = bodies[p].separation(bodies["sun"]).deg
            idx = _pick_idx(sep, alts[p], alts["sun"], alts["sun"], "sun_planet_conjunction")
            if idx is None:
                continue
            if float(sep[idx]) > 3.0:
                continue
            rows.append(
                _event_row(
                    day=d,
                    idx=idx,
                    times_local=times_local,
                    event_type="sun_planet_conjunction",
                    body_a=p,
                    body_b="sun",
                    sep_deg=float(sep[idx]),
                    alt_a=float(alts[p][idx]),
                    alt_b=float(alts["sun"][idx]),
                    sun_alt=float(alts["sun"][idx]),
                    elong_deg=float(sep[idx]),
                    moon_illum=moon_illum,
                )
            )

        d += timedelta(days=1)

    rows.sort(key=lambda r: (r["date_local"], -float(r["score"]), r["event_type"], r["primary_body"], r["secondary_body"]))
    return rows
