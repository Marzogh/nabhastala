from datetime import UTC, datetime

from paa.compute.dark_windows import Interval, intersect, subtract_interval
from paa.compute.sun_moon import _moon_below_horizon_intervals


def test_interval_intersection_minutes() -> None:
    a = Interval(datetime(2027, 1, 1, 10, 0, tzinfo=UTC), datetime(2027, 1, 1, 12, 0, tzinfo=UTC))
    b = Interval(datetime(2027, 1, 1, 11, 0, tzinfo=UTC), datetime(2027, 1, 1, 13, 0, tzinfo=UTC))
    out = intersect(a, b)
    assert out is not None
    assert out.minutes == 60


def test_subtract_interval_middle_cut() -> None:
    base = Interval(
        datetime(2027, 1, 1, 10, 0, tzinfo=UTC), datetime(2027, 1, 1, 14, 0, tzinfo=UTC)
    )
    cut = Interval(datetime(2027, 1, 1, 11, 0, tzinfo=UTC), datetime(2027, 1, 1, 12, 0, tzinfo=UTC))
    pieces = subtract_interval(base, cut)
    assert len(pieces) == 2
    assert pieces[0].minutes == 60
    assert pieces[1].minutes == 120


def test_moon_below_horizon_uses_event_sequence_across_midnight() -> None:
    tz = UTC
    base = Interval(datetime(2027, 1, 1, 19, tzinfo=tz), datetime(2027, 1, 2, 5, tzinfo=tz))
    events = [
        (datetime(2027, 1, 1, 15, tzinfo=tz), "rise"),
        (datetime(2027, 1, 1, 22, tzinfo=tz), "set"),
        (datetime(2027, 1, 2, 8, tzinfo=tz), "rise"),
    ]

    intervals = _moon_below_horizon_intervals(base, events)

    assert intervals == [
        Interval(datetime(2027, 1, 1, 22, tzinfo=tz), datetime(2027, 1, 2, 5, tzinfo=tz))
    ]
