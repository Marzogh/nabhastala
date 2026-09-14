from __future__ import annotations

import math
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from paa.sources.horizons import HorizonsQuery, HorizonsSite, fetch_observer_ephemeris, parse_horizons_observer_ra_dec


def _wrap_delta_ra_deg(moon_ra: float, planet_ra: float) -> float:
    delta = moon_ra - planet_ra
    return (delta + 180.0) % 360.0 - 180.0


def _load_horizons_ids(config_dir: Path) -> dict:
    data = yaml.safe_load((config_dir / "horizons_objects.yaml").read_text(encoding="utf-8")) or {}
    return data


def _read_planet_daily_csv(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return []
    header = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        vals = line.split(",")
        rows.append({header[i]: vals[i] for i in range(min(len(header), len(vals)))})
    return rows


def _best_dates(rows: list[dict], planet_name: str, top_n: int = 3) -> list[str]:
    candidates = [r for r in rows if r.get("planet") == planet_name]
    candidates.sort(key=lambda r: float(r.get("max_altitude_deg", -999.0)), reverse=True)
    dates: list[str] = []
    for r in candidates:
        d = r["date"]
        if d not in dates:
            dates.append(d)
        if len(dates) >= top_n:
            break
    return dates


def _fetch_body_series(target_id: str, date_iso: str, cadence_min: int, site: HorizonsSite) -> dict[datetime, tuple[float, float]]:
    day = datetime.fromisoformat(date_iso).date()
    start = datetime.combine(day, time(0, 0), tzinfo=timezone.utc)
    stop = start + timedelta(days=1)
    raw = fetch_observer_ephemeris(HorizonsQuery(command=target_id, start_utc=start, stop_utc=stop, step_minutes=cadence_min, site=site))
    rows = parse_horizons_observer_ra_dec(raw)
    return {r["datetime_utc"]: (r["ra_deg"], r["dec_deg"]) for r in rows}


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
        ("Jupiter", ids.get("major_planets", {}).get("Jupiter", "599"), ids.get("jupiter_moons", {}), 60),
        ("Saturn", ids.get("major_planets", {}).get("Saturn", "699"), ids.get("saturn_moons", {}), 120),
    ]

    jupiter_rows: list[dict] = []
    saturn_rows: list[dict] = []

    for system_name, planet_id, moon_map, cadence in systems:
        dates = _best_dates(planet_rows, system_name, top_n=3)
        for date_iso in dates:
            planet_series = _fetch_body_series(str(planet_id), date_iso, cadence, site)
            moon_series_map = {moon_name: _fetch_body_series(str(moon_id), date_iso, cadence, site) for moon_name, moon_id in moon_map.items()}

            for moon_name, moon_series in moon_series_map.items():
                for dt_utc, (moon_ra, moon_dec) in moon_series.items():
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
                        "datetime_local": dt_utc.replace(tzinfo=timezone.utc).astimezone(tz).isoformat(),
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
