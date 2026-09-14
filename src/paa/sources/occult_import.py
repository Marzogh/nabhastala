from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _pick_col(headers: list[str], candidates: list[str]) -> int | None:
    lowered = [h.lower().strip() for h in headers]
    for c in candidates:
        for i, h in enumerate(lowered):
            if c in h:
                return i
    return None


def _parse_dt(value: str, timezone_name: str) -> datetime:
    value = value.strip()
    fmts = [
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%b-%d %H:%M",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=ZoneInfo(timezone_name))
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {value}")


def score_occultation(event: dict, cfg: dict) -> str:
    mag = float(event.get("target_mag") or 99.0)
    moon_alt = float(event.get("moon_altitude_deg") or -99.0)
    limb = str(event.get("limb") or "").lower()

    if event.get("is_planetary"):
        base = 3
    elif mag <= float(cfg.get("max_star_mag_imaging", 11)):
        base = 2
    elif mag <= float(cfg.get("max_star_mag_visual", 8)):
        base = 1
    else:
        base = 0

    if moon_alt < float(cfg.get("min_moon_altitude_deg", 10)):
        base -= 1
    if "dark" in limb:
        base += 1

    if base >= 4:
        return "excellent"
    if base >= 3:
        return "good"
    if base >= 2:
        return "fair"
    return "poor"


def import_occult_file(path: Path, timezone_name: str, cfg: dict) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        all_rows = list(reader)
    if not all_rows:
        return rows

    headers = [h.strip() for h in all_rows[0]]
    body = all_rows[1:]

    dt_col = _pick_col(headers, ["datetime", "date", "time"])
    obj_col = _pick_col(headers, ["object", "star", "target", "body"])
    mag_col = _pick_col(headers, ["mag"])
    limb_col = _pick_col(headers, ["limb"])
    moon_alt_col = _pick_col(headers, ["moon alt", "moon_alt", "lunar alt"])
    type_col = _pick_col(headers, ["type", "event"])

    if dt_col is None or obj_col is None:
        raise ValueError("Occult CSV must include datetime/date and object/target columns")

    for raw in body:
        if len(raw) <= max(dt_col, obj_col):
            continue
        dt_local = _parse_dt(raw[dt_col], timezone_name)
        target = raw[obj_col].strip()
        tmag = raw[mag_col].strip() if mag_col is not None and mag_col < len(raw) else ""
        limb = raw[limb_col].strip() if limb_col is not None and limb_col < len(raw) else ""
        moon_alt = raw[moon_alt_col].strip() if moon_alt_col is not None and moon_alt_col < len(raw) else ""
        evtype = raw[type_col].strip() if type_col is not None and type_col < len(raw) else ""

        is_planetary = any(x in target.lower() for x in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]) \
            or "planet" in evtype.lower()

        row = {
            "datetime_local": dt_local.isoformat(),
            "target": target,
            "target_mag": float(tmag) if tmag else None,
            "moon_altitude_deg": float(moon_alt) if moon_alt else None,
            "limb": limb,
            "event_type": evtype,
            "is_planetary": is_planetary,
        }
        row["score"] = score_occultation(row, cfg)
        rows.append(row)

    return rows


def import_latest_occult_cache(year: int, site_id: str, timezone_name: str, cfg: dict) -> list[dict]:
    cache_dir = Path("output") / str(year) / "cache" / "occult" / site_id
    if not cache_dir.exists():
        return []
    candidates = sorted([p for p in cache_dir.iterdir() if p.suffix.lower() in {".csv", ".txt"}], key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return []
    return import_occult_file(candidates[0], timezone_name=timezone_name, cfg=cfg)
