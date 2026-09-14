from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from paa.sources.sbdb import query_comet_candidates
from paa.sources.horizons import HorizonsQuery, HorizonsSite, fetch_observer_ephemeris, parse_horizons_observer_quantities


def _score_row(apmag: float, altitude: float, solar_elong: float) -> tuple[int, str]:
    score = 0
    if apmag <= 8:
        score += 2
    elif apmag <= 10:
        score += 1

    if altitude >= 50:
        score += 2
    elif altitude >= 35:
        score += 1

    if solar_elong >= 90:
        score += 2
    elif solar_elong >= 60:
        score += 1
    else:
        score -= 2

    if altitude < 25:
        score -= 2

    if score >= 5:
        rating = "excellent"
    elif score >= 3:
        rating = "good"
    elif score >= 1:
        rating = "fair"
    else:
        rating = "poor"
    return score, rating


def _best_for_target(
    target: str,
    year: int,
    site: HorizonsSite,
    timezone_name: str,
    step_hours: int,
    max_mag: float,
    min_elong: float,
    min_alt: float,
) -> dict | None:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    stop = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    raw = fetch_observer_ephemeris(
        HorizonsQuery(
            command=target,
            start_utc=start,
            stop_utc=stop,
            step_minutes=step_hours * 60,
            site=site,
            quantities="4,9,20,23",
        )
    )
    rows = parse_horizons_observer_quantities(raw)
    rows = [r for r in rows if r["apmag"] <= max_mag and r["solar_elong_deg"] >= min_elong and r["elevation_deg"] >= min_alt]
    if not rows:
        return None

    best = None
    best_key = None
    for r in rows:
        s, rating = _score_row(r["apmag"], r["elevation_deg"], r["solar_elong_deg"])
        key = (s, r["elevation_deg"], -r["apmag"])
        if best is None or key > best_key:
            best = (r, s, rating)
            best_key = key

    tz = ZoneInfo(timezone_name)
    assert best is not None
    row, s, rating = best
    local = row["datetime_utc"].replace(tzinfo=timezone.utc).astimezone(tz)
    return {
        "target": target,
        "best_datetime_utc": row["datetime_utc"].isoformat(),
        "best_datetime_local": local.isoformat(),
        "best_altitude_deg": round(row["elevation_deg"], 2),
        "best_apmag": round(row["apmag"], 3),
        "solar_elong_deg": round(row["solar_elong_deg"], 3),
        "score": s,
        "rating": rating,
    }


def compute_minor_planets_and_comets(
    year: int,
    site_lat: float,
    site_lon: float,
    site_elev: float,
    timezone_name: str,
    config_dir: Path,
) -> tuple[list[dict], list[dict]]:
    cfg = yaml.safe_load((config_dir / "almanac.yaml").read_text(encoding="utf-8")) or {}
    mp = cfg.get("minor_planets", {})
    com = cfg.get("comets", {})

    site = HorizonsSite(latitude_deg=site_lat, longitude_deg=site_lon, elevation_m=site_elev)

    minor_rows: list[dict] = []
    for target in mp.get("candidates", []):
        try:
            out = _best_for_target(
                target=str(target),
                year=year,
                site=site,
                timezone_name=timezone_name,
                step_hours=int(mp.get("step_hours", 12)),
                max_mag=float(mp.get("max_imaging_mag", 15)),
                min_elong=float(mp.get("min_solar_elongation_deg", 60)),
                min_alt=float(mp.get("min_altitude_deg", 25)),
            )
        except Exception:
            out = None
        if out is not None:
            minor_rows.append(out)

    comet_rows: list[dict] = []
    # Build a broad catalog from SBDB and compute observability for every candidate.
    sbdb_candidates = query_comet_candidates(limit=int(com.get("sbdb_limit", 300)))
    candidate_names: list[str] = []
    for c in sbdb_candidates:
        name = (c.get("pdes") or c.get("full_name") or "").strip()
        if name:
            candidate_names.append(name)
    # Keep explicit config candidates too.
    for c in com.get("candidates", []):
        if str(c) not in candidate_names:
            candidate_names.append(str(c))

    for target in candidate_names:
        base_row = {
            "target": str(target),
            "best_datetime_utc": "",
            "best_datetime_local": "",
            "best_altitude_deg": "",
            "best_apmag": "",
            "solar_elong_deg": "",
            "score": 0,
            "rating": "query_failed",
            "amateur_chaseable": False,
            "source": "computed_catalog",
            "calc_status": "query_failed",
            "magnitude_note": "Predicted magnitude; uncertain.",
        }
        try:
            out = _best_for_target(
                target=str(target),
                year=year,
                site=site,
                timezone_name=timezone_name,
                step_hours=int(com.get("step_hours", 24)),
                max_mag=float(com.get("catalog_max_mag", 22)),
                min_elong=float(com.get("catalog_min_solar_elongation_deg", 20)),
                min_alt=float(com.get("catalog_min_altitude_deg", 5)),
            )
        except Exception:
            comet_rows.append(base_row)
            continue
        if out is None:
            base_row["rating"] = "not_useful"
            base_row["calc_status"] = "not_visible"
            comet_rows.append(base_row)
            continue
        out["amateur_chaseable"] = (
            float(out["best_apmag"]) <= float(com.get("max_mag", 18))
            and float(out["best_altitude_deg"]) >= float(com.get("min_altitude_deg", 15))
            and float(out["solar_elong_deg"]) >= float(com.get("min_solar_elongation_deg", 40))
        )
        out["source"] = "computed_catalog"
        out["calc_status"] = "visible"
        out["magnitude_note"] = "Predicted magnitude; uncertain."
        comet_rows.append(out)

    minor_rows.sort(key=lambda r: (-int(r["score"]), float(r["best_apmag"])))
    comet_rows.sort(
        key=lambda r: (
            0 if r.get("calc_status") == "visible" else (1 if r.get("calc_status") == "not_visible" else 2),
            -int(r.get("score", 0)),
            str(r.get("target", "")),
        )
    )
    return minor_rows, comet_rows
