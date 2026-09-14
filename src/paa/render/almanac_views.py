from __future__ import annotations

import calendar
import csv
from collections import defaultdict
from pathlib import Path

from paa.paths import public_site_slug
from paa.render.view_models import (
    RATING_PRIORITY,
    AnnualOverviewView,
    MonthSummaryView,
    OpportunityView,
    PlanetSeasonView,
    rank_opportunities,
)


def _read_rows(data_dir: Path, filename: str) -> list[dict[str, str]]:
    path = data_dir / filename
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _degrees(value: str | None) -> str:
    number = _number(value)
    return "unknown altitude" if number is None else f"{number:.0f}° altitude"


def _magnitude(value: str | None) -> str:
    number = _number(value)
    return "unknown magnitude" if number is None else f"magnitude {number:.1f}"


def _duration(value: str | None) -> str:
    minutes = _number(value)
    if minutes is None:
        return "duration unavailable"
    hours, remainder = divmod(round(minutes), 60)
    return f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"


def _short_date(value: str) -> str:
    try:
        year, month, day = value[:10].split("-")
        return f"{int(day)} {calendar.month_abbr[int(month)]} {year}"
    except (ValueError, IndexError):
        return value


def _candidate_rows(data_dir: Path) -> list[OpportunityView]:
    candidates: list[OpportunityView] = []
    source_order = 0

    for row in _read_rows(data_dir, "milky_way_windows.csv"):
        quality = row.get("quality", "").lower()
        rating = "excellent" if quality == "excellent" else "good" if quality == "useful" else quality
        candidates.append(
            OpportunityView(
                key=f"milky-way-{source_order}",
                category="Milky Way",
                title="Milky Way core window",
                date_local=row.get("start_local") or row.get("date", ""),
                rating=rating,
                reason=f"{_duration(row.get('duration_minutes'))} with {_degrees(row.get('max_altitude_deg'))}.",
                score=_number(row.get("max_altitude_deg")),
                source_order=source_order,
                complete=bool(row.get("start_local") and row.get("end_local")),
            )
        )
        source_order += 1

    for row in _read_rows(data_dir, "planet_visibility_monthly_summary.csv"):
        candidates.append(
            OpportunityView(
                key=f"planet-{row.get('planet', '')}-{source_order}",
                category="Planets",
                title=row.get("planet", ""),
                date_local=row.get("best_date", ""),
                rating=row.get("rating", ""),
                reason=f"Best monthly date at {_degrees(row.get('best_altitude_deg'))}.",
                source_order=source_order,
                complete=bool(row.get("best_date") and row.get("best_altitude_deg")),
            )
        )
        source_order += 1

    for row in _read_rows(data_dir, "meteor_showers.csv"):
        illumination = _number(row.get("moon_illumination_fraction"))
        moon_note = "Moon interference unavailable"
        if illumination is not None:
            moon_note = f"{illumination:.0%} Moon illumination"
        candidates.append(
            OpportunityView(
                key=f"meteor-{row.get('id', '')}",
                category="Meteor showers",
                title=row.get("name", ""),
                date_local=row.get("peak_date_local", ""),
                rating=row.get("rating", ""),
                reason=f"Peak conditions: {moon_note}; {_degrees(row.get('radiant_alt_predawn_deg'))} predawn.",
                score=_number(row.get("score")),
                source_order=source_order,
                complete=bool(row.get("peak_date_local")),
                include_when_poor=True,
            )
        )
        source_order += 1

    for filename, category in (
        ("minor_planets.csv", "Minor planets"),
        ("comets.csv", "Comets"),
    ):
        for row in _read_rows(data_dir, filename):
            target = row.get("target", "").rstrip(";")
            date_local = row.get("best_datetime_local", "")
            complete = bool(date_local and row.get("best_altitude_deg") and row.get("best_apmag"))
            observable = filename != "comets.csv" or _truthy(row.get("amateur_chaseable"))
            candidates.append(
                OpportunityView(
                    key=f"{category.lower()}-{target}-{source_order}",
                    category=category,
                    title=f"{category[:-1]} {target}",
                    date_local=date_local,
                    rating=row.get("rating", ""),
                    reason=f"{_degrees(row.get('best_altitude_deg'))}; {_magnitude(row.get('best_apmag'))}.",
                    score=_number(row.get("score")),
                    source_order=source_order,
                    observable=observable,
                    complete=complete,
                )
            )
            source_order += 1

    for row in _read_rows(data_dir, "lunar_occultations.csv"):
        candidates.append(
            OpportunityView(
                key=f"occultation-{source_order}",
                category="Occultations",
                title=f"{row.get('target', '').strip()} lunar occultation".strip(),
                date_local=row.get("datetime_local", ""),
                rating=row.get("rating", "good"),
                reason="A locally listed lunar occultation.",
                score=_number(row.get("score")),
                source_order=source_order,
                complete=bool(row.get("datetime_local") and row.get("target")),
            )
        )
        source_order += 1

    return candidates


def rank_diverse_opportunities(
    candidates: list[OpportunityView],
    *,
    limit: int,
) -> tuple[OpportunityView, ...]:
    """Prefer one item per category, then fill remaining slots by normal rank."""
    if limit < 0:
        raise ValueError("Highlight limit cannot be negative")
    if limit == 0:
        return ()
    ranked = rank_opportunities(candidates, limit=len(candidates))
    chosen: list[OpportunityView] = []
    categories: set[str] = set()
    for candidate in ranked:
        if candidate.category not in categories:
            chosen.append(candidate)
            categories.add(candidate.category)
        if len(chosen) == limit:
            return tuple(chosen)
    for candidate in ranked:
        if candidate not in chosen:
            chosen.append(candidate)
        if len(chosen) == limit:
            break
    return tuple(chosen)


def _planet_seasons(data_dir: Path) -> tuple[PlanetSeasonView, ...]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_rows(data_dir, "planet_visibility_monthly_summary.csv"):
        if row.get("planet") and row.get("best_date"):
            grouped[row["planet"]].append(row)

    seasons: list[PlanetSeasonView] = []
    for planet, rows in grouped.items():
        rows.sort(
            key=lambda row: (
                -RATING_PRIORITY.get(row.get("rating", "").lower(), 0),
                -(_number(row.get("best_altitude_deg")) or -1),
                row.get("best_date", ""),
            )
        )
        best = rows[0]
        seasons.append(
            PlanetSeasonView(
                planet=planet,
                best_date=best["best_date"],
                best_altitude_deg=_number(best.get("best_altitude_deg")),
                rating=best.get("rating", "unavailable"),
            )
        )
    return tuple(sorted(seasons, key=lambda item: item.planet.casefold()))


def build_annual_overview(year: int, site_id: str, data_dir: Path) -> AnnualOverviewView:
    candidates = _candidate_rows(data_dir)
    highlights = rank_diverse_opportunities(candidates, limit=6)

    moon_by_month: dict[int, dict[str, str]] = {}
    for row in _read_rows(data_dir, "moon_phase.csv"):
        date = row.get("date", "")
        illumination = _number(row.get("moon_illumination_fraction"))
        if not date.startswith(f"{year}-") or illumination is None:
            continue
        month = int(date[5:7])
        current = moon_by_month.get(month)
        if current is None or illumination < float(current["illumination"]):
            moon_by_month[month] = {"date": date, "illumination": str(illumination)}

    dark_by_month: dict[int, dict[str, str]] = {}
    for row in _read_rows(data_dir, "moon_dark_windows.csv"):
        date = row.get("date", "")
        duration = _number(row.get("duration_minutes"))
        if not date.startswith(f"{year}-") or duration is None:
            continue
        month = int(date[5:7])
        current = dark_by_month.get(month)
        if current is None or duration > float(current["duration_minutes"]):
            dark_by_month[month] = row

    milky_by_month = {
        int(row["month"][5:7]): row
        for row in _read_rows(data_dir, "milky_way_monthly_summary.csv")
        if row.get("month", "").startswith(f"{year}-")
    }

    months: list[MonthSummaryView] = []
    for month in range(1, 13):
        moon = moon_by_month.get(month)
        illumination = float(moon["illumination"]) if moon else None
        moon_state = "Moon data unavailable"
        if moon:
            moon_state = f"Darkest Moon {_short_date(moon['date'])} · {illumination:.0%} illuminated"

        dark = dark_by_month.get(month)
        best_dark = None
        if dark:
            best_dark = f"{_short_date(dark['date'])} · {_duration(dark.get('duration_minutes'))}"

        month_candidates = [
            candidate
            for candidate in candidates
            if candidate.date_local[5:7] == f"{month:02d}"
        ]
        month_highlights = rank_diverse_opportunities(month_candidates, limit=2)
        milky = milky_by_month.get(month, {})
        excellent_milky = int(float(milky.get("excellent_count", "0") or 0))
        if excellent_milky:
            rating = "excellent"
            lead_category = "Milky Way"
            verdict = f"{excellent_milky} excellent Milky Way windows make this a strong deep-sky month."
        elif month_highlights:
            rating = month_highlights[0].rating.lower()
            lead_category = month_highlights[0].category
            verdict = f"{month_highlights[0].title} is the clearest planning lead this month."
        elif best_dark:
            rating = "fair"
            lead_category = "Dark sky"
            verdict = "Use the longest Moon-free window for general observing."
        else:
            rating = "unavailable"
            lead_category = "No recommendation"
            verdict = "No strong opportunity is identified in the available data."

        months.append(
            MonthSummaryView(
                month=month,
                verdict=verdict,
                rating=rating,
                best_dark_window=best_dark,
                moon_state=moon_state,
                highlights=month_highlights,
                month_name=calendar.month_name[month],
                href=f"months/{month:02d}.html",
                lead_category=lead_category,
                moon_illumination=illumination,
            )
        )

    return AnnualOverviewView(
        year=year,
        site_id=site_id,
        site_slug=public_site_slug(site_id),
        months=tuple(months),
        highlights=highlights,
        planet_seasons=_planet_seasons(data_dir),
    )
