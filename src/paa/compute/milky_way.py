from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class MilkyWayPoint:
    timestamp_local: datetime
    altitude_deg: float


def _imports():
    try:
        import matplotlib.pyplot as plt  # type: ignore
        from astropy import units as u  # type: ignore
        from astropy.coordinates import AltAz, EarthLocation, SkyCoord  # type: ignore
        from astropy.time import Time  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Milky Way milestone requires astropy and matplotlib. Install project dependencies first."
        ) from exc
    return plt, u, AltAz, EarthLocation, SkyCoord, Time


def _parse_windows(dark_windows_csv: Path) -> list[tuple[datetime, datetime]]:
    out: list[tuple[datetime, datetime]] = []
    with dark_windows_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append((datetime.fromisoformat(row["start_local"]), datetime.fromisoformat(row["end_local"])))
    return out


def _scan_gc_altitudes(
    windows: list[tuple[datetime, datetime]],
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    step_minutes: int,
) -> list[MilkyWayPoint]:
    _, u, AltAz, EarthLocation, SkyCoord, Time = _imports()
    loc = EarthLocation(lat=latitude_deg * u.deg, lon=longitude_deg * u.deg, height=elevation_m * u.m)
    gc = SkyCoord(ra=266.4051 * u.deg, dec=-28.936175 * u.deg, frame="icrs")

    points: list[MilkyWayPoint] = []
    step = timedelta(minutes=step_minutes)
    for start, end in windows:
        t = start
        while t <= end:
            altaz = gc.transform_to(AltAz(obstime=Time(t), location=loc))
            points.append(MilkyWayPoint(timestamp_local=t, altitude_deg=float(altaz.alt.deg)))
            t += step
    return points


def _group_visibility_windows(
    points: list[MilkyWayPoint], useful_alt_deg: float, excellent_alt_deg: float, step_minutes: int
) -> list[dict]:
    if not points:
        return []

    windows: list[dict] = []
    current: dict | None = None
    gap_limit = timedelta(minutes=step_minutes * 1.5)

    for p in points:
        if p.altitude_deg < useful_alt_deg:
            if current is not None:
                windows.append(current)
                current = None
            continue

        quality = "excellent" if p.altitude_deg >= excellent_alt_deg else "useful"
        if current is None:
            current = {
                "start_local": p.timestamp_local,
                "end_local": p.timestamp_local,
                "max_altitude_deg": p.altitude_deg,
                "quality": quality,
            }
            continue

        if p.timestamp_local - current["end_local"] > gap_limit:
            windows.append(current)
            current = {
                "start_local": p.timestamp_local,
                "end_local": p.timestamp_local,
                "max_altitude_deg": p.altitude_deg,
                "quality": quality,
            }
            continue

        current["end_local"] = p.timestamp_local
        current["max_altitude_deg"] = max(current["max_altitude_deg"], p.altitude_deg)
        if quality == "excellent":
            current["quality"] = "excellent"

    if current is not None:
        windows.append(current)

    rows: list[dict] = []
    for w in windows:
        dur = (w["end_local"] - w["start_local"]).total_seconds() / 60.0 + step_minutes
        rows.append(
            {
                "date": w["start_local"].date().isoformat(),
                "start_local": w["start_local"].isoformat(),
                "end_local": w["end_local"].isoformat(),
                "duration_minutes": round(dur, 1),
                "max_altitude_deg": round(float(w["max_altitude_deg"]), 2),
                "quality": w["quality"],
            }
        )
    return rows


def compute_milky_way_outputs(
    dark_windows_csv: Path,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    useful_alt_deg: float,
    excellent_alt_deg: float,
    step_minutes: int,
) -> tuple[list[dict], list[dict], list[MilkyWayPoint]]:
    windows = _parse_windows(dark_windows_csv)
    points = _scan_gc_altitudes(windows, latitude_deg, longitude_deg, elevation_m, step_minutes)
    visibility = _group_visibility_windows(points, useful_alt_deg, excellent_alt_deg, step_minutes)

    monthly: dict[str, dict] = {}
    for row in visibility:
        month = row["date"][0:7]
        info = monthly.setdefault(month, {"month": month, "window_count": 0, "excellent_count": 0, "best_altitude_deg": -90.0})
        info["window_count"] += 1
        if row["quality"] == "excellent":
            info["excellent_count"] += 1
        info["best_altitude_deg"] = max(float(info["best_altitude_deg"]), float(row["max_altitude_deg"]))

    monthly_rows = []
    for month in sorted(monthly):
        m = monthly[month]
        monthly_rows.append(
            {
                "month": m["month"],
                "window_count": m["window_count"],
                "excellent_count": m["excellent_count"],
                "best_altitude_deg": round(float(m["best_altitude_deg"]), 2),
            }
        )

    return visibility, monthly_rows, points


def save_milky_way_chart(points: list[MilkyWayPoint], path: Path) -> None:
    plt, _, _, _, _, _ = _imports()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not points:
        plt.figure(figsize=(10, 4))
        plt.title("Milky Way Core Altitude During Dark Windows")
        plt.text(0.5, 0.5, "No points", ha="center", va="center")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        return

    x = [p.timestamp_local for p in points]
    y = [p.altitude_deg for p in points]
    plt.figure(figsize=(12, 4))
    plt.plot(x, y, linewidth=0.6)
    plt.axhline(20, linestyle="--", linewidth=0.8)
    plt.axhline(25, linestyle=":", linewidth=0.8)
    plt.title("Milky Way Core Altitude During Dark Windows")
    plt.ylabel("Altitude (deg)")
    plt.xlabel("Local time")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
