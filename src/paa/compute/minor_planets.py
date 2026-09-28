from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

from paa.sources.horizons import (
    HorizonsQuery,
    HorizonsSite,
    fetch_observer_ephemeris,
    parse_horizons_observer_quantities,
)
from paa.sources.sbdb import query_comet_candidates

LOGGER = logging.getLogger(__name__)


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
    command: str,
    year: int,
    site: HorizonsSite,
    timezone_name: str,
    step_hours: int,
    max_mag: float,
    min_elong: float,
    min_alt: float,
    cache_path: Path | None = None,
    permit_missing_magnitude: bool = False,
) -> dict | None:
    start = datetime(year, 1, 1, tzinfo=UTC)
    stop = datetime(year + 1, 1, 1, tzinfo=UTC)
    raw = fetch_observer_ephemeris(
        HorizonsQuery(
            command=command,
            start_utc=start,
            stop_utc=stop,
            step_minutes=step_hours * 60,
            site=site,
            quantities="4,9,20,23",
        ),
        cache_path=cache_path,
    )
    rows = parse_horizons_observer_quantities(raw)
    geometrically_useful = [
        row
        for row in rows
        if row["solar_elong_deg"] >= min_elong and row["elevation_deg"] >= min_alt
    ]
    numeric_magnitudes = [row for row in geometrically_useful if row["apmag"] is not None]
    rows = [row for row in numeric_magnitudes if float(row["apmag"]) <= max_mag]
    if not rows and not (permit_missing_magnitude and geometrically_useful and not numeric_magnitudes):
        return None

    if not rows:
        row = max(
            geometrically_useful,
            key=lambda item: (item["elevation_deg"], item["solar_elong_deg"]),
        )
        tz = ZoneInfo(timezone_name)
        local = row["datetime_utc"].replace(tzinfo=UTC).astimezone(tz)
        return {
            "target": target,
            "best_datetime_utc": row["datetime_utc"].isoformat(),
            "best_datetime_local": local.isoformat(),
            "best_altitude_deg": round(row["elevation_deg"], 2),
            "best_apmag": "",
            "solar_elong_deg": round(row["solar_elong_deg"], 3),
            "score": 0,
            "rating": "unavailable",
        }

    best = None
    best_key = None
    for r in rows:
        magnitude = float(r["apmag"])
        s, rating = _score_row(magnitude, r["elevation_deg"], r["solar_elong_deg"])
        key = (s, r["elevation_deg"], -magnitude)
        if best is None or key > best_key:
            best = (r, s, rating)
            best_key = key

    tz = ZoneInfo(timezone_name)
    assert best is not None
    row, s, rating = best
    local = row["datetime_utc"].replace(tzinfo=UTC).astimezone(tz)
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
    cache_dir: Path | None = None,
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
                command=str(target),
                year=year,
                site=site,
                timezone_name=timezone_name,
                step_hours=int(mp.get("step_hours", 12)),
                max_mag=float(mp.get("max_imaging_mag", 15)),
                min_elong=float(mp.get("min_solar_elongation_deg", 60)),
                min_alt=float(mp.get("min_altitude_deg", 25)),
                cache_path=(
                    cache_dir / "minor-planets" / f"{hashlib.sha256(str(target).encode()).hexdigest()[:16]}.txt"
                    if cache_dir is not None
                    else None
                ),
            )
        except (requests.RequestException, OSError, ValueError, KeyError, TypeError) as exc:
            LOGGER.warning("Minor-planet query failed for %s: %s", target, exc)
            out = None
        if out is not None:
            minor_rows.append(out)

    comet_rows: list[dict] = []
    # Build a broad catalog from SBDB and compute observability for every candidate.
    sbdb_candidates = query_comet_candidates(
        limit=int(com.get("sbdb_limit", 300)),
        cache_path=cache_dir / "sbdb-comets.json" if cache_dir is not None else None,
    )
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
        command = f"DES={target};CAP"
        cache_key = hashlib.sha256(command.encode()).hexdigest()[:16]
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
                command=command,
                year=year,
                site=site,
                timezone_name=timezone_name,
                step_hours=int(com.get("step_hours", 24)),
                max_mag=float(com.get("catalog_max_mag", 22)),
                min_elong=float(com.get("catalog_min_solar_elongation_deg", 20)),
                min_alt=float(com.get("catalog_min_altitude_deg", 5)),
                cache_path=(
                    cache_dir / "comets" / f"{cache_key}.txt"
                    if cache_dir is not None
                    else None
                ),
                permit_missing_magnitude=True,
            )
        except (requests.RequestException, OSError, ValueError, KeyError, TypeError) as exc:
            LOGGER.warning("Comet query failed for %s: %s", target, exc)
            comet_rows.append(base_row)
            continue
        if out is None:
            base_row["rating"] = "not_useful"
            base_row["calc_status"] = "not_visible"
            comet_rows.append(base_row)
            continue
        has_magnitude = out["best_apmag"] != ""
        out["amateur_chaseable"] = (
            has_magnitude
            and float(out["best_apmag"]) <= float(com.get("max_mag", 18))
            and float(out["best_altitude_deg"]) >= float(com.get("min_altitude_deg", 15))
            and float(out["solar_elong_deg"]) >= float(com.get("min_solar_elongation_deg", 40))
        )
        out["source"] = "computed_catalog"
        out["calc_status"] = "visible" if has_magnitude else "magnitude_unavailable"
        out["magnitude_note"] = (
            "JPL Horizons total magnitude; comet brightness remains uncertain."
            if has_magnitude
            else "JPL Horizons did not provide a usable total magnitude."
        )
        comet_rows.append(out)

    minor_rows.sort(key=lambda r: (-int(r["score"]), float(r["best_apmag"])))
    comet_rows.sort(
        key=lambda r: (
            {
                "visible": 0,
                "magnitude_unavailable": 1,
                "not_visible": 2,
                "query_failed": 3,
            }.get(str(r.get("calc_status")), 4),
            -int(r.get("score", 0)),
            str(r.get("target", "")),
        )
    )
    return minor_rows, comet_rows
