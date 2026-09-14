from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from paa.compute.dark_windows import Interval, subtract_many
from paa.models import Site


def _astral_imports():
    try:
        from astral import Observer  # type: ignore
        from astral.moon import moonrise, moonset, phase  # type: ignore
        from astral.sun import sun  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Milestone 1 build requires 'astral'. Install dependencies first (e.g. pip install -e .)."
        ) from exc
    return Observer, sun, phase, moonrise, moonset


def generate_sun_moon_tables(year: int, site: Site) -> tuple[list[dict], list[dict], list[dict]]:
    Observer, sun, moon_phase, moonrise, moonset = _astral_imports()
    tz = ZoneInfo(site.timezone)
    observer = Observer(latitude=site.latitude_deg, longitude=site.longitude_deg, elevation=site.elevation_m)

    twilight_rows: list[dict] = []
    moon_phase_rows: list[dict] = []
    moonrise_rows: list[dict] = []

    day = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    one_day = timedelta(days=1)

    while day < end:
        s = sun(observer, date=day, tzinfo=tz)
        try:
            moon_rise = moonrise(observer, date=day, tzinfo=tz)
        except ValueError:
            moon_rise = None
        try:
            moon_set = moonset(observer, date=day, tzinfo=tz)
        except ValueError:
            moon_set = None

        twilight_rows.append(
            {
                "date": day.isoformat(),
                "dusk_astronomical_local": s["dusk"].isoformat(),
                "dawn_astronomical_local": s["dawn"].isoformat(),
            }
        )
        moon_phase_rows.append(
            {
                "date": day.isoformat(),
                "moon_phase_index": float(moon_phase(day)),
                "moon_illumination_fraction": _phase_to_illumination_fraction(float(moon_phase(day))),
            }
        )
        moonrise_rows.append(
            {
                "date": day.isoformat(),
                "moonrise_local": moon_rise.isoformat() if moon_rise else "",
                "moonset_local": moon_set.isoformat() if moon_set else "",
            }
        )
        day += one_day

    return twilight_rows, moon_phase_rows, moonrise_rows


def _phase_to_illumination_fraction(phase_index: float) -> float:
    # Astral phase: 0=new, 7=first quarter, 14=full, 21=last quarter.
    import math

    angle = (phase_index / 29.53058867) * 2 * math.pi
    return (1 - math.cos(angle)) / 2


def build_dark_windows(
    twilight_rows: list[dict], moon_phase_rows: list[dict], moonrise_rows: list[dict], min_dark_minutes: int, max_illum: float
) -> list[dict]:
    phase_by_date = {row["date"]: row for row in moon_phase_rows}

    dark_rows: list[dict] = []
    for tw in twilight_rows:
        d = tw["date"]
        base = Interval(
            start=datetime.fromisoformat(tw["dusk_astronomical_local"]),
            end=datetime.fromisoformat(tw["dawn_astronomical_local"]),
        )
        if base.end <= base.start:
            # Astronomical dawn is next day in local wall time.
            base = Interval(start=base.start, end=base.end + timedelta(days=1))

        cuts: list[Interval] = []
        phase = phase_by_date[d]
        illum = float(phase["moon_illumination_fraction"])
        rise_row = next((m for m in moonrise_rows if m["date"] == d), None)

        if rise_row and illum > max_illum:
            rise = rise_row["moonrise_local"]
            set_ = rise_row["moonset_local"]
            if rise and set_:
                rise_dt = datetime.fromisoformat(rise)
                set_dt = datetime.fromisoformat(set_)
                if set_dt <= rise_dt:
                    set_dt += timedelta(days=1)
                cuts.append(Interval(start=rise_dt, end=set_dt))

        remaining = subtract_many(base, cuts)
        for w in remaining:
            minutes = w.minutes
            if minutes < min_dark_minutes:
                continue
            dark_rows.append(
                {
                    "date": d,
                    "start_local": w.start.isoformat(),
                    "end_local": w.end.isoformat(),
                    "duration_minutes": round(minutes, 1),
                    "moon_illumination_fraction": round(illum, 3),
                }
            )

    return dark_rows
