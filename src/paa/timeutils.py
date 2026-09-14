from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def to_local(dt_utc: datetime, timezone: str) -> datetime:
    if dt_utc.tzinfo is None:
        raise ValueError("Expected timezone-aware UTC datetime")
    return dt_utc.astimezone(ZoneInfo(timezone))


def local_midnight(year: int, month: int, day: int, timezone: str) -> datetime:
    return datetime(year, month, day, 0, 0, 0, tzinfo=ZoneInfo(timezone))
