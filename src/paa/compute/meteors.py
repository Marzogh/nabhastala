from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


def _imports():
    try:
        from astropy import units as u  # type: ignore
        from astropy.coordinates import AltAz, EarthLocation, SkyCoord  # type: ignore
        from astropy.time import Time  # type: ignore
        from astral.moon import phase  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Meteor computation requires astropy and astral") from exc
    return u, AltAz, EarthLocation, SkyCoord, Time, phase


def _illum_from_phase_index(phase_index: float) -> float:
    import math

    angle = (phase_index / 29.53058867) * 2 * math.pi
    return (1 - math.cos(angle)) / 2


def _score(alt_predawn: float, moon_illum: float, zhr: float) -> tuple[int, str]:
    score = 0
    if alt_predawn >= 60:
        score += 3
    elif alt_predawn >= 40:
        score += 2
    elif alt_predawn >= 20:
        score += 1

    if moon_illum <= 0.2:
        score += 2
    elif moon_illum <= 0.5:
        score += 1
    else:
        score -= 1

    if zhr >= 80:
        score += 2
    elif zhr >= 40:
        score += 1

    if score >= 6:
        return score, "excellent"
    if score >= 4:
        return score, "good"
    if score >= 2:
        return score, "fair"
    return score, "poor"


def compute_meteor_showers(year: int, site_lat: float, site_lon: float, site_elev: float, timezone_name: str, config_dir: Path) -> list[dict]:
    u, AltAz, EarthLocation, SkyCoord, Time, phase = _imports()
    cfg = yaml.safe_load((config_dir / "meteor_showers.yaml").read_text(encoding="utf-8")) or {}
    showers = cfg.get("showers", [])

    loc = EarthLocation(lat=site_lat * u.deg, lon=site_lon * u.deg, height=site_elev * u.m)
    tz = ZoneInfo(timezone_name)

    rows: list[dict] = []
    for s in showers:
        mmdd = str(s.get("typical_peak_mmdd", "01-01"))
        peak_date = datetime.fromisoformat(f"{year}-{mmdd}T00:00:00").date()
        peak_local = datetime(peak_date.year, peak_date.month, peak_date.day, 22, 0, tzinfo=tz)
        predawn_local = datetime(peak_date.year, peak_date.month, peak_date.day, 4, 0, tzinfo=tz)

        radiant = SkyCoord(ra=float(s.get("radiant_ra_hours", 0.0)) * 15.0 * u.deg, dec=float(s.get("radiant_dec_deg", 0.0)) * u.deg, frame="icrs")
        alt_peak = radiant.transform_to(AltAz(obstime=Time(peak_local), location=loc)).alt.deg
        alt_predawn = radiant.transform_to(AltAz(obstime=Time(predawn_local), location=loc)).alt.deg

        moon_phase_idx = float(phase(peak_date))
        moon_illum = _illum_from_phase_index(moon_phase_idx)

        score, rating = _score(float(alt_predawn), float(moon_illum), float(s.get("zhr", 0)))

        rows.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "peak_date_local": peak_date.isoformat(),
                "radiant_alt_peak_deg": round(float(alt_peak), 2),
                "radiant_alt_predawn_deg": round(float(alt_predawn), 2),
                "moon_illumination_fraction": round(float(moon_illum), 3),
                "zhr": float(s.get("zhr", 0)),
                "score": int(score),
                "rating": rating,
                "notes": s.get("notes", ""),
            }
        )

    rows.sort(key=lambda r: (r["peak_date_local"], r["name"]))
    return rows
