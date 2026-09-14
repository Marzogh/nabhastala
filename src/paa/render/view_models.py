from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from html import escape
from math import inf
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LABEL_OVERRIDES = {
    "apmag": "Apparent magnitude",
    "datetime_local": "Local date and time",
    "datetime_utc": "UTC date and time",
    "id": "ID",
    "moon_illumination_fraction": "Moon illumination",
    "ra": "Right ascension",
    "utc": "UTC",
    "zhr": "Zenithal hourly rate",
}

MISSING_VALUES = {"", "none", "null", "nan", "n/a"}
RATING_TONES = {
    "excellent": "excellent",
    "good": "good",
    "fair": "fair",
    "poor": "poor",
    "query_failed": "unavailable",
    "unavailable": "unavailable",
}
RATING_PRIORITY = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}


@dataclass(frozen=True)
class OpportunityView:
    """A renderer-owned candidate; its score is copied, never recalculated."""

    key: str
    category: str
    title: str
    date_local: str
    rating: str
    reason: str
    score: float | None = None
    source_order: int = 0
    observable: bool = True
    complete: bool = True
    include_when_poor: bool = False


@dataclass(frozen=True)
class MonthSummaryView:
    month: int
    verdict: str
    rating: str
    best_dark_window: str | None
    moon_state: str
    highlights: tuple[OpportunityView, ...] = ()
    month_name: str = ""
    href: str = ""
    lead_category: str = "General observing"
    moon_illumination: float | None = None

    def __post_init__(self) -> None:
        _validate_month(self.month)
        if len(self.highlights) > 2:
            raise ValueError("A month summary can contain at most two highlights")


@dataclass(frozen=True)
class AnnualOverviewView:
    year: int
    site_id: str
    site_slug: str
    months: tuple[MonthSummaryView, ...]
    highlights: tuple[OpportunityView, ...] = ()
    planet_seasons: tuple[PlanetSeasonView, ...] = ()

    def __post_init__(self) -> None:
        if tuple(month.month for month in self.months) != tuple(range(1, 13)):
            raise ValueError("An annual overview requires months 1 through 12 in order")
        if len(self.highlights) > 6:
            raise ValueError("An annual overview can contain at most six highlights")


@dataclass(frozen=True)
class PlanetSeasonView:
    planet: str
    best_date: str
    best_altitude_deg: float | None
    rating: str


@dataclass(frozen=True)
class MonthGuideView:
    year: int
    month: int
    site_id: str
    site_slug: str
    verdict: str
    highlights: tuple[OpportunityView, ...] = ()

    def __post_init__(self) -> None:
        _validate_month(self.month)
        if len(self.highlights) > 5:
            raise ValueError("A monthly guide can contain at most five highlights")


def _validate_month(month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month: {month!r}")
    return month


def opportunity_is_eligible(candidate: OpportunityView) -> bool:
    """Return whether a candidate can appear in an editorial highlight list."""
    rating = candidate.rating.strip().lower()
    if not (
        candidate.observable
        and candidate.complete
        and candidate.title.strip()
        and candidate.reason.strip()
        and candidate.date_local.strip()
    ):
        return False
    if rating == "poor":
        return candidate.include_when_poor
    return rating in {"excellent", "good", "fair"}


def rank_opportunities(
    candidates: Iterable[OpportunityView],
    *,
    limit: int,
    month: int | None = None,
) -> tuple[OpportunityView, ...]:
    """Select eligible highlights using a stable, documented display order."""
    if limit < 0:
        raise ValueError("Highlight limit cannot be negative")
    if month is not None:
        _validate_month(month)

    eligible = [
        candidate
        for candidate in candidates
        if opportunity_is_eligible(candidate)
        and (month is None or candidate.date_local[5:7] == f"{month:02d}")
    ]
    eligible.sort(
        key=lambda candidate: (
            -RATING_PRIORITY[candidate.rating.strip().lower()],
            -(candidate.score if candidate.score is not None else -inf),
            candidate.date_local,
            candidate.source_order,
            candidate.title.casefold(),
        )
    )
    return tuple(eligible[:limit])


def humanize_label(name: str) -> str:
    key = name.strip().lower()
    if key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[key]
    return key.replace("_", " ").strip().capitalize()


def format_local_datetime(value: object, timezone_name: str | None = None) -> str:
    text = str(value).strip()
    if text.lower() in MISSING_VALUES:
        return "—"
    try:
        parsed = datetime.fromisoformat(text)
        if timezone_name and parsed.tzinfo is not None:
            parsed = parsed.astimezone(ZoneInfo(timezone_name))
    except (ValueError, ZoneInfoNotFoundError):
        return text

    hour = parsed.strftime("%I").lstrip("0") or "0"
    rendered = f"{parsed.day} {parsed.strftime('%b %Y')}, {hour}:{parsed.strftime('%M %p').lower()}"
    if parsed.tzinfo is not None:
        zone = parsed.tzname()
        if zone:
            rendered += f" {zone}"
    return rendered


def format_local_date(value: object, *, include_year: bool = False) -> str:
    text = str(value).strip()
    if text.lower() in MISSING_VALUES:
        return "—"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    rendered = f"{parsed.day} {parsed.strftime('%b')}"
    return f"{rendered} {parsed.year}" if include_year else rendered


def rating_tone(value: object) -> str:
    return RATING_TONES.get(str(value).strip().lower(), "neutral")


def format_display_value(
    column: str,
    value: object,
    *,
    timezone_name: str | None = None,
) -> str:
    if value is None or str(value).strip().lower() in MISSING_VALUES:
        return "—"
    text = str(value).strip()
    key = column.lower()
    if "datetime" in key or key.endswith(("_local", "_utc")):
        return format_local_datetime(text, timezone_name)
    if key == "moon_illumination_fraction":
        try:
            return f"{float(text):.0%}"
        except ValueError:
            return text
    if text.lower() in {"true", "false"}:
        return "Yes" if text.lower() == "true" else "No"
    if key in {"rating", "score"} and not text.replace(".", "", 1).isdigit():
        return text.replace("_", " ").capitalize()
    return text


def escape_display(value: object) -> str:
    """Escape display text for the current pre-template renderer."""
    return escape(str(value), quote=True)
