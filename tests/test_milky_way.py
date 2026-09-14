from datetime import datetime, timedelta, timezone

from paa.compute.milky_way import MilkyWayPoint


def test_milky_way_point_dataclass() -> None:
    t0 = datetime(2027, 1, 1, 19, 0, tzinfo=timezone.utc)
    p = MilkyWayPoint(timestamp_local=t0, altitude_deg=21.5)
    assert p.altitude_deg > 20
    assert p.timestamp_local + timedelta(minutes=10) > p.timestamp_local
