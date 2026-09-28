from __future__ import annotations

import calendar
import csv
import math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from paa.paths import public_site_slug
from paa.render.view_models import (
    RATING_PRIORITY,
    AnnualOverviewView,
    DownloadView,
    MilkyWaySessionView,
    MonthGuideView,
    MonthSummaryView,
    MoonSampleView,
    NightWindowView,
    OpportunityView,
    PlanetGroupView,
    PlanetMonthView,
    PlanetSeasonView,
    rank_opportunities,
)

MINOR_PLANET_NAMES = {
    "1": "1 Ceres",
    "2": "2 Pallas",
    "3": "3 Juno",
    "4": "4 Vesta",
    "7": "7 Iris",
    "15": "15 Eunomia",
}


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


def _moon_illuminated_path(phase_index: float, illumination: float) -> str:
    """Return an illuminated lunar-disc path for Astral's 0 to 29.53 phase index."""
    centre = 50.0
    radius = 46.0
    if illumination <= 0.002:
        return ""
    if illumination >= 0.998:
        return f"M {centre - radius:.2f} {centre:.2f} a {radius} {radius} 0 1 0 {radius * 2:.2f} 0 a {radius} {radius} 0 1 0 {-radius * 2:.2f} 0"

    phase = (phase_index % 29.53058867) / 29.53058867
    waxing = phase <= 0.5
    cosine = math.cos(phase * 2 * math.pi)
    points: list[tuple[float, float]] = []
    steps = 48
    for step in range(steps + 1):
        y = -radius + (2 * radius * step / steps)
        limb = math.sqrt(max(0.0, radius**2 - y**2))
        x = centre + (limb if waxing else -limb)
        points.append((x, centre + y))
    for step in range(steps, -1, -1):
        y = -radius + (2 * radius * step / steps)
        limb = math.sqrt(max(0.0, radius**2 - y**2))
        terminator = cosine * limb if waxing else -cosine * limb
        points.append((centre + terminator, centre + y))
    return "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in points) + " Z"


def _short_date(value: str) -> str:
    try:
        year, month, day = value[:10].split("-")
        return f"{int(day)} {calendar.month_abbr[int(month)]} {year}"
    except (ValueError, IndexError):
        return value


def _short_time(value: str) -> str:
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    hour = moment.hour % 12 or 12
    suffix = "am" if moment.hour < 12 else "pm"
    return f"{hour}:{moment.minute:02d} {suffix}"


def _best_milky_windows(year: int, data_dir: Path) -> dict[int, dict[str, str]]:
    best: dict[int, dict[str, str]] = {}
    for row in _read_rows(data_dir, "milky_way_windows.csv"):
        date_value = row.get("date", "")
        if not date_value.startswith(f"{year}-"):
            continue
        try:
            month = int(date_value[5:7])
        except ValueError:
            continue
        current = best.get(month)
        rank = (
            _number(row.get("max_altitude_deg")) or -90,
            _number(row.get("duration_minutes")) or 0,
        )
        current_rank = (
            (_number(current.get("max_altitude_deg")) or -90),
            (_number(current.get("duration_minutes")) or 0),
        ) if current else (-90, 0)
        if current is None or rank > current_rank:
            best[month] = row
    return best


def _planet_oppositions(year: int, data_dir: Path) -> dict[int, dict[str, str]]:
    """Find outer-planet opposition dates from maximum annual solar elongation."""
    best_by_planet: dict[str, dict[str, str]] = {}
    for row in _read_rows(data_dir, "planet_visibility_daily.csv"):
        date_value = row.get("date", "")
        planet = row.get("planet", "")
        elongation = _number(row.get("solar_elong_deg"))
        if (
            not date_value.startswith(f"{year}-")
            or planet not in {"Jupiter", "Saturn", "Uranus", "Neptune"}
            or elongation is None
        ):
            continue
        current = best_by_planet.get(planet)
        if current is None or elongation > (_number(current.get("solar_elong_deg")) or -1):
            best_by_planet[planet] = row

    by_month: dict[int, dict[str, str]] = {}
    for row in best_by_planet.values():
        elongation = _number(row.get("solar_elong_deg")) or 0
        if elongation < 170:
            continue
        month = int(row["date"][5:7])
        current = by_month.get(month)
        if current is None or abs(180 - elongation) < abs(
            180 - (_number(current.get("solar_elong_deg")) or 0)
        ):
            by_month[month] = row
    return by_month


def _notable_meteors(year: int, data_dir: Path) -> dict[int, dict[str, str]]:
    by_month: dict[int, dict[str, str]] = {}
    for row in _read_rows(data_dir, "meteor_showers.csv"):
        date_value = row.get("peak_date_local", "")
        rating = row.get("rating", "").lower()
        if not date_value.startswith(f"{year}-") or rating not in {"good", "excellent"}:
            continue
        month = int(date_value[5:7])
        current = by_month.get(month)
        if current is None or RATING_PRIORITY.get(rating, 0) > RATING_PRIORITY.get(
            current.get("rating", "").lower(), 0
        ):
            by_month[month] = row
    return by_month


def _night_minute(value: datetime) -> float:
    minutes = value.hour * 60 + value.minute
    if minutes < 12 * 60:
        minutes += 24 * 60
    return max(0.0, min(720.0, minutes - 18 * 60))


def _milky_way_instrument(year: int, data_dir: Path) -> dict[str, object]:
    year_start = date(year, 1, 1)
    year_days = (date(year + 1, 1, 1) - year_start).days
    windows: list[dict[str, object]] = []
    for row in _read_rows(data_dir, "milky_way_windows.csv"):
        try:
            start = datetime.fromisoformat(row["start_local"])
            end = datetime.fromisoformat(row["end_local"])
            day_index = (date.fromisoformat(row["date"]) - year_start).days
        except (KeyError, ValueError):
            continue
        if not 0 <= day_index < year_days:
            continue
        start_minute = _night_minute(start)
        end_minute = _night_minute(end)
        if end_minute <= start_minute:
            end_minute = min(720.0, start_minute + (_number(row.get("duration_minutes")) or 0))
        windows.append(
            {
                "date": row["date"],
                "day": day_index,
                "start_local": row["start_local"],
                "end_local": row["end_local"],
                "start_pct": start_minute / 720 * 100,
                "height_pct": max(1.5, (end_minute - start_minute) / 720 * 100),
                "duration_minutes": _number(row.get("duration_minutes")) or 0,
                "max_altitude_deg": _number(row.get("max_altitude_deg")),
                "quality": row.get("quality", "useful"),
            }
        )
    month_ticks = [
        {
            "label": calendar.month_abbr[month],
            "day": (date(year, month, 1) - year_start).days,
        }
        for month in range(1, 13)
    ]
    best_by_month: dict[int, dict[str, object]] = {}
    for window in windows:
        month = int(str(window["date"])[5:7])
        current = best_by_month.get(month)
        if current is None or (
            float(window["duration_minutes"]),
            float(window["max_altitude_deg"] or -90),
        ) > (float(current["duration_minutes"]), float(current["max_altitude_deg"] or -90)):
            best_by_month[month] = window
    summaries = tuple(
        {
            "month_name": calendar.month_abbr[month],
            **best_by_month[month],
        }
        for month in range(1, 13)
        if month in best_by_month
    )
    return {
        "year_days": year_days,
        "windows": windows,
        "month_ticks": month_ticks,
        "summaries": summaries,
    }


def _planet_instrument(year: int, data_dir: Path) -> dict[str, object]:
    rows = _read_rows(data_dir, "planet_visibility_monthly_summary.csv")
    by_planet: dict[str, dict[int, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        try:
            month = int(row.get("month", "")[5:7])
        except ValueError:
            continue
        if not row.get("month", "").startswith(f"{year}-"):
            continue
        by_planet[row.get("planet", "")][month] = {
            "month": month,
            "best_date": row.get("best_date", ""),
            "best_time_local": row.get("best_time_local", ""),
            "altitude_deg": _number(row.get("best_altitude_deg")),
            "rating": row.get("rating", "unavailable"),
            "period": row.get("observation_period", "unavailable"),
        }
    order = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune")
    return {
        "months": tuple(calendar.month_abbr[month] for month in range(1, 13)),
        "lanes": tuple(
            {
                "planet": planet,
                "months": tuple(by_planet.get(planet, {}).get(month) for month in range(1, 13)),
            }
            for planet in order
        ),
    }


def _moon_instrument(year: int, data_dir: Path, filename: str, system: str) -> dict[str, object]:
    rows = _read_rows(data_dir, filename)
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("date") and row.get("datetime_local"):
            by_date[row["date"]].append(row)
    nights: list[dict[str, object]] = []
    for night_date, night_rows in sorted(by_date.items()):
        parsed = []
        for row in night_rows:
            try:
                parsed.append((row, datetime.fromisoformat(row["datetime_local"])))
            except ValueError:
                continue
        if not parsed:
            continue
        start = min(item[1] for item in parsed)
        end = max(item[1] for item in parsed)
        span_seconds = max(1.0, (end - start).total_seconds())
        extent = max(1.0, max(abs(_number(row.get("dra_arcsec")) or 0) for row, _ in parsed))
        moons = tuple(sorted({row.get("moon", "") for row, _ in parsed}))
        moon_index = {name: index for index, name in enumerate(moons)}
        points = []
        for row, timestamp in parsed:
            offset = _number(row.get("dra_arcsec")) or 0
            points.append(
                {
                    "moon": row.get("moon", ""),
                    "moon_index": moon_index[row.get("moon", "")],
                    "datetime_local": row.get("datetime_local", ""),
                    "offset_arcsec": offset,
                    "x_pct": 50 + offset / extent * 46,
                    "y_pct": (timestamp - start).total_seconds() / span_seconds * 100,
                }
            )
        nights.append(
            {
                "date": night_date,
                "start_local": start.isoformat(),
                "end_local": end.isoformat(),
                "extent_arcsec": extent,
                "moons": moons,
                "points": points,
            }
        )
    return {
        "system": system,
        "year": year,
        "default_date": nights[0]["date"] if nights else f"{year}-01-01",
        "nights": nights,
    }


def build_observing_instruments(year: int, data_dir: Path) -> dict[str, object]:
    """Build deterministic chart models from the same reviewed CSVs as the prose."""
    return {
        "milky_way": _milky_way_instrument(year, data_dir),
        "planets": _planet_instrument(year, data_dir),
        "moon_systems": (
            _moon_instrument(year, data_dir, "jupiter_moons.csv", "Jupiter"),
            _moon_instrument(year, data_dir, "saturn_moons.csv", "Saturn"),
        ),
    }


def _candidate_rows(data_dir: Path) -> list[OpportunityView]:
    candidates: list[OpportunityView] = []
    source_order = 0

    for row in _read_rows(data_dir, "milky_way_windows.csv"):
        quality = row.get("quality", "").lower()
        rating = (
            "excellent" if quality == "excellent" else "good" if quality == "useful" else quality
        )
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
            title = (
                MINOR_PLANET_NAMES.get(target, f"Minor planet {target}")
                if filename == "minor_planets.csv"
                else f"Comet {target}"
            )
            date_local = row.get("best_datetime_local", "")
            complete = bool(date_local and row.get("best_altitude_deg") and row.get("best_apmag"))
            observable = filename != "comets.csv" or _truthy(row.get("amateur_chaseable"))
            candidates.append(
                OpportunityView(
                    key=f"{category.lower()}-{target}-{source_order}",
                    category=category,
                    title=title,
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

    occultation_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in _read_rows(data_dir, "lunar_occultations.csv"):
        occultation_groups[(row.get("target", ""), row.get("datetime_local", "")[:10])].append(row)
    for rows in occultation_groups.values():
        rows.sort(key=lambda item: item.get("datetime_local", ""))
        row = next(
            (
                item
                for item in rows
                if "disappearance" in item.get("event_type", "").lower()
            ),
            rows[0],
        )
        times = " to ".join(_short_time(item.get("datetime_local", "")) for item in rows)
        altitude = _degrees(row.get("moon_altitude_deg"))
        candidates.append(
            OpportunityView(
                key=f"occultation-{source_order}",
                category="Occultations",
                title=f"{row.get('target', '').strip()} lunar occultation".strip(),
                date_local=row.get("datetime_local", ""),
                rating=row.get("score", "fair"),
                reason=f"{times}; Moon at {altitude} for the first listed contact.",
                score=None,
                source_order=source_order,
                complete=bool(row.get("datetime_local") and row.get("target")),
            )
        )
        source_order += 1

    for row in _read_rows(data_dir, "astronomical_phenomena.csv"):
        event = row.get("event", "")
        visibility = row.get("visibility", "")
        visible = "below horizon" not in visibility.lower()
        if "eclipse" in event.lower():
            rating = "excellent" if visible else "poor"
            category = "Eclipses"
            title = event
            reason_parts = [visibility, row.get("value", "")]
        elif event == "Opposition" or "elongation" in event.lower():
            rating = "good"
            category = "Planetary events"
            title = f"{row.get('target', '')} {event.lower()}".strip()
            reason_parts = (
                ["Visible for most of the night"]
                if event == "Opposition"
                else [visibility, f"{row.get('value', '')} from the Sun"]
            )
        else:
            rating = "fair"
            category = "Planetary events"
            title = f"{row.get('target', '')} stationary point".strip()
            reason_parts = ["Apparent motion changes direction"]
        reason_parts = [part for part in reason_parts if part]
        candidates.append(
            OpportunityView(
                key=f"phenomenon-{source_order}",
                category=category,
                title=title,
                date_local=row.get("datetime_local", ""),
                rating=rating,
                reason="; ".join(reason_parts) + ".",
                source_order=source_order,
                observable=visible,
                complete=bool(row.get("datetime_local") and event),
                include_when_poor=False,
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

    milky_by_month = _best_milky_windows(year, data_dir)
    oppositions_by_month = _planet_oppositions(year, data_dir)
    meteors_by_month = _notable_meteors(year, data_dir)

    months: list[MonthSummaryView] = []
    for month in range(1, 13):
        moon = moon_by_month.get(month)
        illumination = float(moon["illumination"]) if moon else None
        moon_state = "Moon data unavailable"
        if moon:
            moon_state = (
                f"Darkest Moon {_short_date(moon['date'])} · {illumination:.0%} illuminated"
            )

        dark = dark_by_month.get(month)
        best_dark = None
        if dark:
            best_dark = f"{_short_date(dark['date'])} · {_duration(dark.get('duration_minutes'))}"

        month_candidates = [
            candidate for candidate in candidates if candidate.date_local[5:7] == f"{month:02d}"
        ]
        month_highlights = rank_diverse_opportunities(month_candidates, limit=2)
        opposition = oppositions_by_month.get(month)
        meteor = meteors_by_month.get(month)
        milky = milky_by_month.get(month)
        if opposition:
            planet = opposition.get("planet", "A planet")
            best_time = opposition.get("twilight_best_time_local") or opposition.get(
                "best_time_local", ""
            )
            rating = opposition.get("visibility_rating", "excellent").lower()
            lead_category = "Planet opposition"
            verdict = f"{planet} reaches opposition on {_short_date(opposition['date'])}"
            verdict += f" and is highest around {_short_time(best_time)}." if best_time else "."
        elif meteor:
            name = meteor.get("name") or meteor.get("id", "Meteor shower").replace("_", " ").title()
            illumination = _number(meteor.get("moon_illumination_fraction"))
            radiant = _number(meteor.get("radiant_alt_predawn_deg"))
            rating = meteor.get("rating", "good").lower()
            lead_category = "Meteor shower"
            verdict = f"{name} peak on {_short_date(meteor['peak_date_local'])}"
            if illumination is not None:
                verdict += f" under {illumination:.0%} Moon"
            if radiant is not None and radiant < 10:
                verdict += ", though the radiant stays low from this horizon."
            elif radiant is not None:
                verdict += f", with the radiant reaching about {radiant:.0f}° before dawn."
            else:
                verdict += "."
        elif milky:
            rating = "excellent" if milky.get("quality", "").lower() == "excellent" else "good"
            lead_category = "Galactic Centre"
            verdict = (
                f"Galactic Centre viewing is best on {_short_date(milky['date'])}, "
                f"from {_short_time(milky.get('start_local', ''))} to "
                f"{_short_time(milky.get('end_local', ''))}"
            )
            altitude = _number(milky.get("max_altitude_deg"))
            verdict += f", reaching {altitude:.0f}°." if altitude is not None else "."
        elif month_highlights:
            rating = month_highlights[0].rating.lower()
            lead_category = month_highlights[0].category
            verdict = f"{month_highlights[0].title}: {month_highlights[0].reason}"
        elif best_dark:
            rating = "fair"
            lead_category = "Dark sky"
            verdict = f"Longest low-Moon dark period: {best_dark}."
        else:
            rating = "unavailable"
            lead_category = "No recommendation"
            verdict = "No major event listed."

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


def _month_rows(data_dir: Path, filename: str, year: int, month: int) -> list[dict[str, str]]:
    prefix = f"{year}-{month:02d}"
    rows = _read_rows(data_dir, filename)
    date_fields = ("date", "month", "peak_date_local", "best_date", "datetime_local")
    return [
        row for row in rows if any(row.get(field, "").startswith(prefix) for field in date_fields)
    ]


def _observation_period(value: str) -> str:
    try:
        hour = int(value[11:13])
    except (ValueError, IndexError):
        return "Overnight"
    if 17 <= hour < 22:
        return "Evening"
    if hour >= 22 or hour < 4:
        return "Overnight"
    return "Predawn"


def build_month_guide(
    year: int,
    month: int,
    site_id: str,
    data_dir: Path,
) -> MonthGuideView:
    candidates = _candidate_rows(data_dir)
    month_candidates = [
        candidate for candidate in candidates if candidate.date_local[5:7] == f"{month:02d}"
    ]
    highlights = rank_diverse_opportunities(month_candidates, limit=5)

    moon_rows = _month_rows(data_dir, "moon_phase.csv", year, month)
    moon_values = [(row, _number(row.get("moon_illumination_fraction"))) for row in moon_rows]
    moon_values = [(row, value) for row, value in moon_values if value is not None]
    new_moon = min(moon_values, key=lambda item: item[1])[0] if moon_values else None
    full_moon = max(moon_values, key=lambda item: item[1])[0] if moon_values else None
    moon_samples_list: list[MoonSampleView] = []
    for row, value in moon_values[::7][:5]:
        phase_index = _number(row.get("moon_phase_index"))
        if phase_index is None:
            phase_index = math.acos(max(-1.0, min(1.0, 1 - 2 * value))) * 29.53058867 / math.pi
        moon_samples_list.append(
            MoonSampleView(
                date=row.get("date", ""),
                illumination=value,
                phase_index=phase_index,
                illuminated_path=_moon_illuminated_path(phase_index, value),
            )
        )
    moon_samples = tuple(moon_samples_list)

    twilight_rows = _month_rows(data_dir, "sun_twilight.csv", year, month)
    representative = (
        min(
            twilight_rows,
            key=lambda row: abs(int(row.get("date", "00")[-2:]) - 15),
        )
        if twilight_rows
        else None
    )

    phase_by_date = {row.get("date", ""): row for row in moon_rows}
    rise_set_by_date = {
        row.get("date", ""): row
        for row in _month_rows(data_dir, "moonrise_moonset.csv", year, month)
    }
    dark_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _month_rows(data_dir, "moon_dark_windows.csv", year, month):
        dark_by_date[row.get("date", "")].append(row)
    milky_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _month_rows(data_dir, "milky_way_windows.csv", year, month):
        milky_by_date[row.get("date", "")].append(row)
    planets_by_date: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in _month_rows(data_dir, "planet_visibility_daily.csv", year, month):
        altitude = _number(row.get("twilight_max_altitude_deg"))
        if altitude is None or altitude <= 0 or not row.get("twilight_best_time_local"):
            continue
        planets_by_date[row.get("date", "")].append(
            {
                "planet": row.get("planet", ""),
                "time": row.get("twilight_best_time_local", ""),
                "altitude": altitude,
                "rating": row.get("visibility_rating", "unavailable"),
            }
        )
    night_plans = tuple(
        {
            "date": row.get("date", ""),
            "dusk": row.get("dusk_astronomical_local", ""),
            "dawn": row.get("dawn_astronomical_local", ""),
            "illumination": _number(
                phase_by_date.get(row.get("date", ""), {}).get("moon_illumination_fraction")
            ),
            "moonrise": rise_set_by_date.get(row.get("date", ""), {}).get("moonrise_local", ""),
            "moonset": rise_set_by_date.get(row.get("date", ""), {}).get("moonset_local", ""),
            "dark": [
                {"start": item.get("start_local", ""), "end": item.get("end_local", "")}
                for item in dark_by_date.get(row.get("date", ""), [])
            ],
            "milky": [
                {
                    "start": item.get("start_local", ""),
                    "end": item.get("end_local", ""),
                    "altitude": _number(item.get("max_altitude_deg")),
                    "quality": item.get("quality", "useful"),
                }
                for item in milky_by_date.get(row.get("date", ""), [])
            ],
            "planets": sorted(
                planets_by_date.get(row.get("date", ""), []),
                key=lambda item: (-float(item["altitude"]), str(item["planet"])),
            ),
        }
        for row in sorted(twilight_rows, key=lambda item: item.get("date", ""))
    )

    dark_rows = _month_rows(data_dir, "moon_dark_windows.csv", year, month)
    dark_rows.sort(
        key=lambda row: (-(_number(row.get("duration_minutes")) or 0), row.get("date", ""))
    )
    dark_windows = tuple(
        NightWindowView(
            date=row.get("date", ""),
            start_local=row.get("start_local", ""),
            end_local=row.get("end_local", ""),
            duration_minutes=_number(row.get("duration_minutes")) or 0,
            moon_illumination=_number(row.get("moon_illumination_fraction")),
        )
        for row in dark_rows[:3]
    )

    milky_rows = _month_rows(data_dir, "milky_way_windows.csv", year, month)
    milky_rows = [
        row
        for row in milky_rows
        if row.get("quality", "").lower() in {"excellent", "useful"}
        and _number(row.get("duration_minutes")) is not None
        and _number(row.get("max_altitude_deg")) is not None
    ]
    milky_rows.sort(
        key=lambda row: (
            -RATING_PRIORITY["excellent" if row["quality"].lower() == "excellent" else "good"],
            -(_number(row.get("duration_minutes")) or 0),
            -(_number(row.get("max_altitude_deg")) or 0),
            row.get("date", ""),
        )
    )
    milky_sessions = tuple(
        MilkyWaySessionView(
            date=row.get("date", ""),
            start_local=row.get("start_local", ""),
            end_local=row.get("end_local", ""),
            duration_minutes=_number(row.get("duration_minutes")) or 0,
            max_altitude_deg=_number(row.get("max_altitude_deg")) or 0,
            rating="excellent" if row["quality"].lower() == "excellent" else "good",
        )
        for row in milky_rows[:3]
    )

    daily_planets = {
        (row.get("planet", ""), row.get("date", "")): row
        for row in _month_rows(data_dir, "planet_visibility_daily.csv", year, month)
    }
    planet_buckets: dict[str, list[PlanetMonthView]] = defaultdict(list)
    for row in _month_rows(data_dir, "planet_visibility_monthly_summary.csv", year, month):
        daily = daily_planets.get((row.get("planet", ""), row.get("best_date", "")))
        if not daily:
            continue
        altitude = _number(daily.get("twilight_max_altitude_deg"))
        best_time = daily.get("twilight_best_time_local", "")
        rating = row.get("rating", "").lower()
        if altitude is None or altitude <= 0 or rating not in RATING_PRIORITY:
            continue
        period = _observation_period(best_time)
        planet_buckets[period].append(
            PlanetMonthView(
                planet=row.get("planet", ""),
                best_date=row.get("best_date", ""),
                best_time_local=best_time,
                altitude_deg=altitude,
                rating=rating,
                period=period,
            )
        )
    planet_groups = tuple(
        PlanetGroupView(
            period=period,
            planets=tuple(
                sorted(
                    planet_buckets[period],
                    key=lambda item: (
                        -RATING_PRIORITY[item.rating],
                        -item.altitude_deg,
                        item.planet,
                    ),
                )
            ),
        )
        for period in ("Evening", "Overnight", "Predawn")
        if planet_buckets[period]
    )

    other = rank_diverse_opportunities(
        [
            candidate
            for candidate in month_candidates
            if candidate.category not in {"Milky Way", "Planets"}
        ],
        limit=3,
    )
    data_notes: list[str] = []
    failed_comets = sum(
        row.get("calc_status", "").lower() == "query_failed"
        for row in _read_rows(data_dir, "comets.csv")
    )
    if failed_comets:
        data_notes.append(
            f"Positions are unavailable for {failed_comets} comet entries."
        )
    if not _month_rows(data_dir, "lunar_occultations.csv", year, month):
        data_notes.append("No lunar occultation is listed for this month.")
    else:
        data_notes.append(
            "Occultation times use a smooth lunar limb; confirm grazing events with IOTA Occult 4."
        )

    annual_month = build_annual_overview(year, site_id, data_dir).months[month - 1]
    verdict = annual_month.verdict
    rating = annual_month.rating

    download_names = (
        ("Twilight", "sun_twilight.csv"),
        ("Moon phases", "moon_phase.csv"),
        ("Dark windows", "moon_dark_windows.csv"),
        ("Milky Way", "milky_way_windows.csv"),
        ("Planets", "planet_visibility_daily.csv"),
        ("Eclipses and planetary events", "astronomical_phenomena.csv"),
        ("Events", "meteor_showers.csv"),
    )
    downloads = tuple(
        DownloadView(label, filename)
        for label, filename in download_names
        if (data_dir / filename).exists()
    )

    return MonthGuideView(
        year=year,
        month=month,
        site_id=site_id,
        site_slug=public_site_slug(site_id),
        verdict=verdict,
        highlights=highlights,
        rating=rating,
        month_name=calendar.month_name[month],
        new_moon_date=new_moon.get("date") if new_moon else None,
        full_moon_date=full_moon.get("date") if full_moon else None,
        representative_date=representative.get("date") if representative else None,
        dusk_local=representative.get("dusk_astronomical_local") if representative else None,
        dawn_local=representative.get("dawn_astronomical_local") if representative else None,
        planner_default_date=(
            dark_windows[0].date
            if dark_windows
            else representative.get("date")
            if representative
            else None
        ),
        night_plans=night_plans,
        moon_samples=moon_samples,
        dark_windows=dark_windows,
        milky_way_sessions=milky_sessions,
        planet_groups=planet_groups,
        other_opportunities=other,
        data_notes=tuple(data_notes),
        downloads=downloads,
    )
