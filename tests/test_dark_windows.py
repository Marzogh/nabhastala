from datetime import datetime, timezone

from paa.compute.dark_windows import Interval, intersect, subtract_interval


def test_interval_intersection_minutes() -> None:
    a = Interval(datetime(2027, 1, 1, 10, 0, tzinfo=timezone.utc), datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc))
    b = Interval(datetime(2027, 1, 1, 11, 0, tzinfo=timezone.utc), datetime(2027, 1, 1, 13, 0, tzinfo=timezone.utc))
    out = intersect(a, b)
    assert out is not None
    assert out.minutes == 60


def test_subtract_interval_middle_cut() -> None:
    base = Interval(datetime(2027, 1, 1, 10, 0, tzinfo=timezone.utc), datetime(2027, 1, 1, 14, 0, tzinfo=timezone.utc))
    cut = Interval(datetime(2027, 1, 1, 11, 0, tzinfo=timezone.utc), datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc))
    pieces = subtract_interval(base, cut)
    assert len(pieces) == 2
    assert pieces[0].minutes == 60
    assert pieces[1].minutes == 120
