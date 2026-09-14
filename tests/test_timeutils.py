from datetime import datetime, timezone

from paa.timeutils import to_local


def test_to_local_brisbane_conversion() -> None:
    dt_utc = datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc)
    local = to_local(dt_utc, "Australia/Brisbane")
    assert local.hour == 22
    assert local.tzinfo is not None
