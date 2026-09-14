from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _fmt_date(value: str | None) -> str:
    if not value:
        return "TBC"
    return datetime.fromisoformat(value).strftime("%b %d")


def _fmt_time(value: str | None) -> str:
    if not value:
        return "--"
    return datetime.fromisoformat(value).strftime("%H:%M")


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _in_night_window(best_time_local: str | None, dusk_local: str | None, dawn_local: str | None) -> bool:
    if not best_time_local or not dusk_local or not dawn_local:
        return False
    try:
        t = datetime.fromisoformat(best_time_local)
        dusk = datetime.fromisoformat(dusk_local)
        dawn = datetime.fromisoformat(dawn_local)
    except ValueError:
        return False

    # For per-date summaries, night spans [00:00..dawn] U [dusk..23:59].
    return t <= dawn or t >= dusk


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def generate_ui_notes(
    *,
    year: int,
    site_name: str,
    timezone: str,
    dark_rows: list[dict[str, Any]],
    moon_phase_rows: list[dict[str, Any]],
    moonrise_rows: list[dict[str, Any]],
    twilight_rows: list[dict[str, Any]],
    milky_monthly_rows: list[dict[str, Any]],
    milky_rows: list[dict[str, Any]],
    planet_daily_rows: list[dict[str, Any]],
    planet_monthly_rows: list[dict[str, Any]],
    minor_rows: list[dict[str, Any]],
    comet_rows: list[dict[str, Any]],
    occult_rows: list[dict[str, Any]],
    meteor_rows: list[dict[str, Any]],
    conjunction_rows: list[dict[str, Any]],
    validation_items: list[tuple[str, bool]],
) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []

    def add(note_id: str, section: str, title: str, body: str, score: str = "info", date_local: str | None = None) -> None:
        notes.append(
            {
                "note_id": note_id,
                "section": section,
                "title": title,
                "body": body,
                "score": score,
                "date_local": date_local or "",
            }
        )

    def _event_kind(title: str) -> str:
        t = title.lower()
        if t.startswith("dark-sky"):
            return "dark"
        if t.startswith("milky way"):
            return "milkyway"
        if "observing window" in t:
            for p in ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"):
                if p in t:
                    return f"planet-{p}"
            return "planet"
        if t.startswith("minor planet"):
            return "minor"
        if t.startswith("comet:"):
            return "comet"
        if t.startswith("meteor shower"):
            return "meteor"
        if "conjunction" in t or "transit" in t:
            return "conjunction"
        if t.startswith("lunar occultation"):
            return "occultation"
        return "event"

    add(
        "hero_subtitle",
        "hero",
        "Context",
        f"Generated for {site_name}. Times shown in {timezone}.",
    )

    dark0 = dark_rows[0] if dark_rows else {}
    moon0 = moon_phase_rows[0] if moon_phase_rows else {}
    rise0 = moonrise_rows[0] if moonrise_rows else {}
    illum = _safe_float(moon0.get("moon_illumination_fraction"))
    illum_pct = int(round(illum * 100)) if illum is not None else None

    tonight_score = "Fair"
    if illum is not None and illum <= 0.1:
        tonight_score = "Excellent"
    elif illum is not None and illum <= 0.35:
        tonight_score = "Good"
    elif illum is not None and illum >= 0.7:
        tonight_score = "Poor"

    add(
        "tonight_score",
        "tonight",
        tonight_score,
        (
            f"Astronomical dark {_fmt_time(dark0.get('start_local'))} to {_fmt_time(dark0.get('end_local'))}. "
            f"Moon illumination {illum_pct if illum_pct is not None else '--'}%."
        ),
        tonight_score.lower(),
        dark0.get("date"),
    )
    add(
        "moon_summary",
        "moon",
        f"{illum_pct if illum_pct is not None else '--'}%",
        (
            f"Moon rises {_fmt_time(rise0.get('moonrise_local'))}, sets {_fmt_time(rise0.get('moonset_local'))}. "
            "Use moon-free windows first for deep sky."
        ),
        "info",
        rise0.get("date"),
    )

    candidates: list[dict[str, Any]] = []
    # Dark windows
    twilight_by_date = {str(r.get("date", "")): r for r in twilight_rows}
    for r in dark_rows:
        dur = _safe_float(r.get("duration_minutes")) or 0
        ill = _safe_float(r.get("moon_illumination_fraction")) or 1
        d = str(r.get("date", ""))
        tw = twilight_by_date.get(d, {})

        # Strict moon_dark_window gate for imaging usability:
        # - moon illumination must be faint enough
        # - and a meaningful fraction of astronomical darkness must be moon-free
        dusk = _parse_iso(str(tw.get("dusk_astronomical_local", "")))
        dawn_raw = _parse_iso(str(tw.get("dawn_astronomical_local", "")))
        dark_minutes = 0.0
        if dusk and dawn_raw:
            dawn = dawn_raw
            if dawn <= dusk:
                dawn = dawn + timedelta(days=1)
            dark_minutes = max(0.0, (dawn - dusk).total_seconds() / 60.0)
        free_share = (dur / dark_minutes) if dark_minutes > 0 else 0.0
        if not (ill <= 0.35 and free_share >= 0.5):
            continue

        raw = dur / 60.0 + max(0, (0.5 - ill) * 4.0)
        if ill >= 0.7:
            raw = min(raw, 4.9)
        score = "excellent" if raw >= 8 else "good" if raw >= 5 else "fair"
        if ill <= 0.35:
            moon_note = f"Low moon interference ({int(round(ill * 100))}%)."
        elif ill <= 0.7:
            moon_note = f"Moderate moon interference ({int(round(ill * 100))}%)."
        else:
            moon_note = f"High moon interference ({int(round(ill * 100))}%)."
        candidates.append(
            {
                "date_local": d,
                "title": "Dark-sky window",
                "body": f"{int(round(dur))} moon-free minutes. {moon_note}",
                "score": score,
                "raw": raw,
            }
        )
    # Milky Way windows
    for r in milky_rows:
        dur = _safe_float(r.get("duration_minutes")) or 0
        alt = _safe_float(r.get("max_altitude_deg")) or 0
        raw = dur / 90.0 + alt / 30.0
        score = "excellent" if raw >= 4 else "good" if raw >= 2.8 else "fair"
        candidates.append(
            {
                "date_local": r.get("date", ""),
                "title": "Milky Way core window",
                "body": f"Core visibility window with max altitude about {int(round(alt))} degrees.",
                "score": score,
                "raw": raw,
            }
        )
    # Planet daily (all computed planets), but only when best time is in local night window.
    inner_planet_alt_cutoffs = {
        "mercury": 10.0,
        "venus": 15.0,
    }
    inner_planet_elong_cutoffs = {
        "mercury": 18.0,
        "venus": 30.0,
    }
    for r in planet_daily_rows:
        pname = str(r.get("planet", "")).strip()
        if not pname:
            continue
        pname_l = pname.lower()
        d = str(r.get("date", ""))
        tw = twilight_by_date.get(d, {})
        is_inner = pname_l in inner_planet_alt_cutoffs
        if is_inner:
            tw_time = str(r.get("twilight_best_time_local", ""))
            tw_alt = _safe_float(r.get("twilight_max_altitude_deg")) or 0
            if not tw_time:
                continue
            min_alt = inner_planet_alt_cutoffs[pname_l]
            if tw_alt < min_alt:
                continue
            min_elong = inner_planet_elong_cutoffs.get(pname_l)
            if min_elong is not None:
                elong = _safe_float(r.get("solar_elong_deg"))
                if elong is None or elong < min_elong:
                    continue
            best_time_local = tw_time
            alt = tw_alt
        else:
            if not _in_night_window(
                str(r.get("best_time_local", "")),
                str(tw.get("dusk_astronomical_local", "")),
                str(tw.get("dawn_astronomical_local", "")),
            ):
                continue
            best_time_local = str(r.get("best_time_local", ""))
            alt = _safe_float(r.get("max_altitude_deg")) or 0
        raw = alt / 20.0
        score = "excellent" if alt >= 60 else "good" if alt >= 40 else "fair"
        timing_note = "Best twilight time" if is_inner else "Best local time"
        candidates.append(
            {
                "date_local": r.get("date", ""),
                "title": f"{pname} observing window",
                "body": f"{timing_note} {best_time_local[11:16]} with altitude near {int(round(alt))} degrees.",
                "score": score,
                "raw": raw,
            }
        )
    # Minor planets
    for r in minor_rows:
        raw = float(r.get("score", 0))
        candidates.append(
            {
                "date_local": str(r.get("best_datetime_local", ""))[:10],
                "title": f"Minor planet: {r.get('target', 'target')}",
                "body": f"Predicted mag {r.get('best_apmag', '--')}, altitude {r.get('best_altitude_deg', '--')} degrees.",
                "score": str(r.get("rating", "fair")).lower(),
                "raw": raw,
            }
        )
    # Comets
    for r in comet_rows:
        if str(r.get("calc_status", "")) != "visible":
            continue
        raw = float(r.get("score", 0))
        candidates.append(
            {
                "date_local": str(r.get("best_datetime_local", ""))[:10],
                "title": f"Comet: {r.get('target', 'target')}",
                "body": f"Predicted mag {r.get('best_apmag', '--')} (uncertain), altitude {r.get('best_altitude_deg', '--')} degrees.",
                "score": str(r.get("rating", "fair")).lower(),
                "raw": raw,
            }
        )
    # Meteors
    for r in meteor_rows:
        raw = float(r.get("score", 0))
        candidates.append(
            {
                "date_local": r.get("peak_date_local", ""),
                "title": f"Meteor shower: {r.get('name', 'shower')}",
                "body": f"Peak night with ZHR {int(float(r.get('zhr', 0)))} and moon illumination {int(float(r.get('moon_illumination_fraction', 0))*100)}%.",
                "score": str(r.get("rating", "fair")).lower(),
                "raw": raw,
            }
        )
    # Occultations
    for r in occult_rows:
        date_local = str(r.get("datetime_local", ""))[:10]
        score = str(r.get("score", "fair")).lower()
        raw = 6 if "excellent" in score else 4 if "good" in score else 2
        candidates.append(
            {
                "date_local": date_local,
                "title": f"Lunar occultation: {r.get('target', 'target')}",
                "body": f"{r.get('event_type', 'Occultation')} event. Limb {r.get('limb', 'n/a')}.",
                "score": score,
                "raw": raw,
            }
        )

    # Conjunctions and transits
    for r in conjunction_rows:
        et = str(r.get("event_type", "")).strip()
        p = str(r.get("primary_body", "")).strip()
        s = str(r.get("secondary_body", "")).strip()
        sep = _safe_float(r.get("separation_deg"))
        alt_p = _safe_float(r.get("alt_primary_deg"))
        alt_s = _safe_float(r.get("alt_secondary_deg"))
        sun_alt = _safe_float(r.get("sun_altitude_deg"))
        visibility = str(r.get("visibility_rating", "fair")).lower()
        raw = _safe_float(r.get("score")) or 0
        date_local = str(r.get("date_local", ""))

        # Keep upcoming list observer-usable: both bodies up and sky dark enough.
        if et in {"planet_planet_conjunction", "moon_planet_conjunction"}:
            if (alt_p is None or alt_s is None or sun_alt is None):
                continue
            if min(alt_p, alt_s) < 10 or sun_alt > -6:
                continue

        if et == "planet_planet_conjunction":
            title = f"{p}-{s} conjunction"
            body = f"Closest approach near {_fmt_time(r.get('event_time_local'))}, separation {sep if sep is not None else '--'} degrees. Altitudes {int(round(alt_p or 0))}/{int(round(alt_s or 0))} degrees."
        elif et == "moon_planet_conjunction":
            title = f"Moon-{s if p.lower() == 'moon' else p} conjunction"
            body = f"Closest approach near {_fmt_time(r.get('event_time_local'))}, separation {sep if sep is not None else '--'} degrees. Moon illumination {int(round((_safe_float(r.get('moon_illumination_fraction')) or 0)*100))}%."
        elif et == "solar_transit":
            if sun_alt is not None and sun_alt <= 0:
                continue
            title = f"{p} solar transit"
            body = f"Near-Sun event around {_fmt_time(r.get('event_time_local'))}. Solar observing safety required."
            visibility = "excellent" if visibility == "excellent" else "fair"
            raw = max(raw, 8)
        else:
            title = f"{p} conjunction with Sun"
            body = f"Near-Sun conjunction around {_fmt_time(r.get('event_time_local'))}. Usually not observable; use for planning transitions."
            visibility = "info"
            raw = max(raw, 1)

        candidates.append(
            {
                "date_local": date_local,
                "title": title,
                "body": body,
                "score": visibility,
                "raw": raw,
            }
        )

    # Deduplicate close duplicates by (date,title) and keep highest raw score.
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for c in candidates:
        k = (str(c.get("date_local", "")), str(c.get("title", "")))
        if k not in merged or float(c.get("raw", 0)) > float(merged[k].get("raw", 0)):
            merged[k] = c
    ranked = sorted(merged.values(), key=lambda c: (str(c.get("date_local", "")), -float(c.get("raw", 0)), str(c.get("title", ""))))
    kind_counters: dict[tuple[str, str], int] = {}
    for c in ranked:
        d = str(c.get("date_local", "")) or "undated"
        k = _event_kind(str(c.get("title", "")))
        key = (d, k)
        kind_counters[key] = kind_counters.get(key, 0) + 1
        note_id = f"event.{d}.{k}.{kind_counters[key]:03d}"
        add(
            note_id,
            "events",
            str(c.get("title", "Event")),
            str(c.get("body", "")),
            str(c.get("score", "info")),
            d if d != "undated" else "",
        )

    mw_best = milky_monthly_rows[0] if milky_monthly_rows else {}
    add(
        "mw_summary",
        "milky_way",
        "Milky Way window",
        (
            f"{mw_best.get('excellent_count', 0)} excellent windows this month group. "
            f"Best altitude about {int(_safe_float(mw_best.get('best_altitude_deg')) or 0)} degrees."
        ),
        "info",
    )

    ok_count = sum(1 for _, ok in validation_items if ok)
    total_count = len(validation_items)
    missing = [name for name, ok in validation_items if not ok]
    missing_txt = ", ".join(missing) if missing else "all core datasets are present"
    add(
        "validation_summary",
        "validation",
        f"{ok_count}/{total_count}",
        f"Validation check: {missing_txt}.",
        "good" if ok_count == total_count else "fair",
    )

    rec_body = "Use deep sky early, then switch to planetary once the Moon is higher."
    if occult_rows:
        rec_body += " Check occultations list for timed events."
    add("recommended_tonight", "recommendations", "Recommended tonight", rec_body, "info")
    return notes
