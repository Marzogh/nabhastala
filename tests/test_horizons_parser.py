from datetime import UTC, datetime

import pytest

from paa.sources.horizons import (
    HorizonsQuery,
    HorizonsSite,
    fetch_observer_ephemeris,
    parse_horizons_csv,
    parse_horizons_observer_quantities,
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


def test_fetch_observer_ephemeris_caches_incomplete_source_response(
    tmp_path, monkeypatch
) -> None:
    cache = tmp_path / "horizons-error.txt"

    class Response:
        text = "No ephemeris for target"

        @staticmethod
        def raise_for_status() -> None:
            return None

    monkeypatch.setattr(
        "paa.sources.horizons.requests.get", lambda *args, **kwargs: Response()
    )
    query = HorizonsQuery(
        command="DES=51P;CAP",
        start_utc=datetime(2026, 1, 1, tzinfo=UTC),
        stop_utc=datetime(2027, 1, 1, tzinfo=UTC),
        step_minutes=1440,
        site=HorizonsSite(-27.5, 153.0, 50),
    )

    with pytest.raises(ValueError, match="complete ephemeris"):
        fetch_observer_ephemeris(query, cache_path=cache)

    assert cache.read_text(encoding="utf-8") == Response.text


def test_parse_comet_total_magnitude_and_missing_nuclear_magnitude() -> None:
    raw = """header
 Date__(UT)__HR:MN, Elev_(a-app), T-mag, N-mag, S-O-T
$$SOE
 2026-Jan-01 00:00, 42.5, 11.7, n.a., 75.0
$$EOE
"""

    rows = parse_horizons_observer_quantities(raw)

    assert rows[0]["apmag"] == 11.7
    assert rows[0]["elevation_deg"] == 42.5
