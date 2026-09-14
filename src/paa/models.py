from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    id: str
    name: str
    latitude_deg: float
    longitude_deg: float
    elevation_m: float
    timezone: str
    bortle: int | None = None


@dataclass(frozen=True)
class RuntimeContext:
    year: int
    site: Site
