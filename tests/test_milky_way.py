from datetime import UTC, datetime, timedelta

from paa.compute.milky_way import MilkyWayPoint, _group_visibility_windows


def test_milky_way_point_dataclass() -> None:
    t0 = datetime(2027, 1, 1, 19, 0, tzinfo=UTC)
    p = MilkyWayPoint(timestamp_local=t0, altitude_deg=21.5)
    assert p.altitude_deg > 20
    assert p.timestamp_local + timedelta(minutes=10) > p.timestamp_local


def test_visibility_window_uses_exclusive_end_and_keeps_nights_separate() -> None:
    first = datetime(2027, 1, 1, 19, 0, tzinfo=UTC)
    second = datetime(2027, 1, 2, 19, 0, tzinfo=UTC)
    rows = _group_visibility_windows(
        [
            MilkyWayPoint(first, 23.0),
            MilkyWayPoint(first + timedelta(minutes=10), 26.0),
            MilkyWayPoint(second, 24.0),
        ],
        useful_alt_deg=20,
        excellent_alt_deg=25,
        step_minutes=10,
    )

    assert len(rows) == 2
    assert rows[0]["end_local"] == (first + timedelta(minutes=20)).isoformat()
    assert rows[0]["duration_minutes"] == 20
    assert rows[1]["duration_minutes"] == 10


def test_visibility_window_keeps_the_observing_night_date_and_clamps_to_dawn() -> None:
    sample = datetime(2027, 1, 2, 4, 50, tzinfo=UTC)
    dawn = sample + timedelta(minutes=5)

    rows = _group_visibility_windows(
        [MilkyWayPoint(sample, 30.0, "2027-01-01", dawn)],
        useful_alt_deg=20,
        excellent_alt_deg=25,
        step_minutes=10,
    )

    assert rows[0]["date"] == "2027-01-01"
    assert rows[0]["end_local"] == dawn.isoformat()
    assert rows[0]["duration_minutes"] == 5
