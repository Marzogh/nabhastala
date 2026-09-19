from __future__ import annotations

import csv
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from paa.sources.horizons import (
    HorizonsQuery,
    HorizonsSite,
    fetch_observer_ephemeris,
    parse_horizons_observer_ra_dec,
)


def _wrap_delta_ra_deg(moon_ra: float, planet_ra: float) -> float:
    delta = moon_ra - planet_ra
    return (delta + 180.0) % 360.0 - 180.0


def _load_horizons_ids(config_dir: Path) -> dict:
    data = yaml.safe_load((config_dir / "horizons_objects.yaml").read_text(encoding="utf-8")) or {}
    return data


def _read_planet_daily_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _best_dates(rows: list[dict], planet_name: str, top_n: int = 3) -> list[str]:
    candidates = [
        row
        for row in rows
        if row.get("planet") == planet_name
        and row.get("best_time_local")
        and row.get("visibility_rating") in {"excellent", "good", "fair"}
    ]
    candidates.sort(key=lambda r: float(r.get("max_altitude_deg", -999.0)), reverse=True)
    dates: list[str] = []
    months: set[str] = set()
    for r in candidates:
        d = r["date"]
        month = d[:7]
        if d not in dates and month not in months:
            dates.append(d)
            months.add(month)
        if len(dates) >= top_n:
            break
    return dates


def _fetch_body_series(
    target_id: str,
    centre_utc: datetime,
    cadence_min: int,
    site: HorizonsSite,
) -> dict[datetime, tuple[float, float]]:
    start = centre_utc - timedelta(hours=5)
    stop = centre_utc + timedelta(hours=5)
    raw = fetch_observer_ephemeris(
        HorizonsQuery(
            command=target_id, start_utc=start, stop_utc=stop, step_minutes=cadence_min, site=site
        )
    )
    rows = parse_horizons_observer_ra_dec(raw)
    return {r["datetime_utc"]: (r["ra_deg"], r["dec_deg"]) for r in rows}


def _observable_timestamps(
    timestamps: list[datetime], site: HorizonsSite, sun_limit_deg: float = -4.0
) -> set[datetime]:
    if not timestamps:
        return set()
    try:
        from astropy import units as u  # type: ignore
        from astropy.coordinates import AltAz, EarthLocation, get_sun  # type: ignore
        from astropy.time import Time  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Moon-system filtering requires astropy.") from exc
    location = EarthLocation(
        lat=site.latitude_deg * u.deg,
        lon=site.longitude_deg * u.deg,
        height=site.elevation_m * u.m,
    )
    utc_times = [timestamp.replace(tzinfo=UTC) for timestamp in timestamps]
    time_array = Time(utc_times)
    sun_altitudes = get_sun(time_array).transform_to(
        AltAz(obstime=time_array, location=location)
    ).alt.deg
    return {
        timestamp
        for timestamp, sun_altitude in zip(timestamps, sun_altitudes, strict=True)
        if float(sun_altitude) <= sun_limit_deg
    }


def compute_moon_offsets(
    year: int,
    site_lat: float,
    site_lon: float,
    site_elev: float,
    site_tz: str,
    config_dir: Path,
    planet_daily_csv: Path,
) -> tuple[list[dict], list[dict]]:
    ids = _load_horizons_ids(config_dir)
    planet_rows = _read_planet_daily_csv(planet_daily_csv)
    site = HorizonsSite(latitude_deg=site_lat, longitude_deg=site_lon, elevation_m=site_elev)
    tz = ZoneInfo(site_tz)

    systems = [
        (
            "Jupiter",
            ids.get("major_planets", {}).get("Jupiter", "599"),
            ids.get("jupiter_moons", {}),
            60,
        ),
        (
            "Saturn",
            ids.get("major_planets", {}).get("Saturn", "699"),
            ids.get("saturn_moons", {}),
            120,
        ),
    ]

    jupiter_rows: list[dict] = []
    saturn_rows: list[dict] = []

    for system_name, planet_id, moon_map, cadence in systems:
        dates = _best_dates(planet_rows, system_name, top_n=3)
        rows_by_date = {row["date"]: row for row in planet_rows if row.get("planet") == system_name}
        for date_iso in dates:
            best_local = datetime.fromisoformat(rows_by_date[date_iso]["best_time_local"])
            centre_utc = best_local.astimezone(UTC).replace(tzinfo=None)
            planet_series = _fetch_body_series(str(planet_id), centre_utc, cadence, site)
            observable_timestamps = _observable_timestamps(list(planet_series), site)
            moon_series_map = {
                moon_name: _fetch_body_series(str(moon_id), centre_utc, cadence, site)
                for moon_name, moon_id in moon_map.items()
            }

            for moon_name, moon_series in moon_series_map.items():
                for dt_utc, (moon_ra, moon_dec) in moon_series.items():
                    if dt_utc not in observable_timestamps:
                        continue
                    planet = planet_series.get(dt_utc)
                    if planet is None:
                        continue
                    p_ra, p_dec = planet
                    dra = _wrap_delta_ra_deg(moon_ra, p_ra) * math.cos(math.radians(p_dec)) * 3600.0
                    ddec = (moon_dec - p_dec) * 3600.0
                    row = {
                        "system": system_name,
                        "date": date_iso,
                        "datetime_utc": dt_utc.isoformat(),
                        "datetime_local": dt_utc.replace(tzinfo=UTC).astimezone(tz).isoformat(),
                        "moon": moon_name,
                        "dra_arcsec": round(dra, 3),
                        "ddec_arcsec": round(ddec, 3),
                    }
                    if system_name == "Jupiter":
                        jupiter_rows.append(row)
                    else:
                        saturn_rows.append(row)

    return jupiter_rows, saturn_rows


def save_moon_strip_chart(rows: list[dict], output_png: Path, title: str) -> None:
    if not rows:
        return
    import matplotlib.pyplot as plt  # type: ignore

    output_png.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["moon"], []).append(row)

    plt.figure(figsize=(8, 6))
    for moon, mrows in grouped.items():
        mrows.sort(key=lambda r: r["datetime_local"])
        x = [float(r["dra_arcsec"]) for r in mrows]
        y = list(range(len(mrows)))
        plt.plot(x, y, marker=".", linewidth=0.8, label=moon)

    plt.axvline(0, linewidth=1.0, linestyle="--")
    plt.title(title)
    plt.xlabel("Relative E-W offset (arcsec)")
    plt.ylabel("Time index")
    plt.legend(loc="best", fontsize=8)
    plt.tight_layout()
    plt.savefig(output_png, bbox_inches="tight")
    plt.close()
