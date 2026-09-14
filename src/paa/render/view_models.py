from __future__ import annotations

from datetime import datetime
from html import escape
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
