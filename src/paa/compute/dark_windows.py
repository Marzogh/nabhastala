from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    @property
    def minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0


def intersect(a: Interval, b: Interval) -> Interval | None:
    start = max(a.start, b.start)
    end = min(a.end, b.end)
    if end <= start:
        return None
    return Interval(start=start, end=end)


def subtract_interval(base: Interval, cut: Interval) -> list[Interval]:
    overlap = intersect(base, cut)
    if overlap is None:
        return [base]

    pieces: list[Interval] = []
    if base.start < overlap.start:
        pieces.append(Interval(start=base.start, end=overlap.start))
    if overlap.end < base.end:
        pieces.append(Interval(start=overlap.end, end=base.end))
    return pieces


def subtract_many(base: Interval, cuts: list[Interval]) -> list[Interval]:
    remaining = [base]
    for cut in cuts:
        next_remaining: list[Interval] = []
        for chunk in remaining:
            next_remaining.extend(subtract_interval(chunk, cut))
        remaining = next_remaining
        if not remaining:
            break
    return remaining
