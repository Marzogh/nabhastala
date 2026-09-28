from datetime import UTC, datetime

import pytest

from paa.sources.horizons import (
    HorizonsQuery,
    HorizonsSite,
    fetch_observer_ephemeris,
    parse_horizons_csv,
)


def test_parse_horizons_csv_happy_path() -> None:
    raw = "header\n$$SOE\n2027-Jan-01 00:00,1,2,3\n2027-Jan-01 01:00,4,5,6\n$$EOE\n"
    rows = parse_horizons_csv(raw)
    assert len(rows) == 2
    assert rows[0][0] == "2027-Jan-01 00:00"


def test_parse_horizons_csv_missing_markers() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_horizons_csv("no markers")


def test_fetch_observer_ephemeris_reuses_local_cache(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "horizons.txt"
    cache.write_text("cached $$SOE\nvalue\n$$EOE", encoding="utf-8")
    monkeypatch.setattr(
        "paa.sources.horizons.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")),
    )
    query = HorizonsQuery(
        command="599",
        start_utc=datetime(2027, 1, 1, tzinfo=UTC),
        stop_utc=datetime(2027, 1, 2, tzinfo=UTC),
        step_minutes=60,
        site=HorizonsSite(-27.5, 153.0, 50),
    )

    assert fetch_observer_ephemeris(query, cache_path=cache).startswith("cached")
