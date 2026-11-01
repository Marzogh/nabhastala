from __future__ import annotations

import csv
import gzip
from datetime import UTC, datetime
from pathlib import Path

from paa.compute.ephemeris import (
    compact_sky_events,
    validate_ephemeris_rows,
    write_deterministic_gzip,
)
from paa.compute.sun_moon import generate_sun_moon_tables
from paa.models import Site


def _row(
    *,
    utc: str,
    local: str,
    object_class: str = "star",
    object_id: str = "HIP 32349",
    event_type: str = "rise",
    altitude: float = -0.5667,
    state: str = "normal",
) -> dict[str, object]:
    return {
        "local_date": datetime.fromisoformat(local).date().isoformat(),
        "object_class": object_class,
        "object_id": object_id,
        "object_name": "Sirius" if object_class == "star" else object_id.title(),
        "magnitude": -1.46 if object_class == "star" else "",
        "event_type": event_type,
        "event_time_utc": utc,
        "event_time_local": local,
        "azimuth_deg": 110.0,
        "altitude_deg": altitude,
        "horizon_state": state,
        "calculation_basis": "test",
    }


def test_validation_accepts_offset_equivalence_dst_and_leap_day() -> None:
    rows = [
        _row(
            utc="2028-02-28T14:30:00+00:00",
            local="2028-02-29T01:30:00+11:00",
        ),
        _row(
            utc="2028-04-04T15:30:00+00:00",
            local="2028-04-05T01:30:00+10:00",
            event_type="set",
        ),
    ]

    assert validate_ephemeris_rows(rows, expected_star_count=1) == []


def test_validation_rejects_duplicate_and_wrong_horizon_altitude() -> None:
    row = _row(
        utc="2026-01-01T09:00:00+00:00",
        local="2026-01-01T19:00:00+10:00",
        altitude=2.0,
    )

    failures = validate_ephemeris_rows([row, row], expected_star_count=1)

    assert any("duplicate event" in failure for failure in failures)
    assert any("threshold tolerance" in failure for failure in failures)


def test_validation_keeps_two_same_type_events_on_one_local_date() -> None:
    rows = [
        _row(
            utc="2026-04-04T13:30:00+00:00",
            local="2026-04-05T00:30:00+11:00",
            event_type="upper_transit",
            altitude=55.0,
        ),
        _row(
            utc="2026-04-05T13:26:00+00:00",
            local="2026-04-05T23:26:00+10:00",
            event_type="upper_transit",
            altitude=55.0,
        ),
    ]

    assert validate_ephemeris_rows(rows, expected_star_count=1) == []


def test_compact_events_use_indexed_minute_offsets() -> None:
    rows = [
        _row(
            utc="2026-01-01T00:01:20+00:00",
            local="2026-01-01T10:01:20+10:00",
        ),
        _row(
            utc="2026-01-01T06:00:00+00:00",
            local="2026-01-01T16:00:00+10:00",
            event_type="upper_transit",
            altitude=61.2,
        ),
    ]

    payload = compact_sky_events(rows, 2026)

    assert payload["objects"]["HIP 32349"]["name"] == "Sirius"
    assert payload["objects"]["HIP 32349"]["events"][0][1] == 1
    assert payload["event_types"]["upper_transit"] == 1


def test_deterministic_gzip_has_stable_bytes(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"
    source.write_text("event\nrise\n", encoding="utf-8")

    write_deterministic_gzip(source, first)
    write_deterministic_gzip(source, second)

    assert first.read_bytes() == second.read_bytes()
    with gzip.open(first, "rt", encoding="utf-8") as handle:
        assert handle.read() == "event\nrise\n"


def test_sun_moon_compatibility_tables_use_ephemeris_events() -> None:
    site = Site(
        id="se_qld",
        name="South East Queensland",
        latitude_deg=-27.5,
        longitude_deg=153.0,
        elevation_m=50,
        timezone="Australia/Brisbane",
    )
    events = [
        _row(
            utc="2026-01-01T09:00:00+00:00",
            local="2026-01-01T19:00:00+10:00",
            object_class="sun",
            object_id="sun",
            event_type="astronomical_dusk",
            altitude=-18.0,
        ),
        _row(
            utc="2025-12-31T18:00:00+00:00",
            local="2026-01-01T04:00:00+10:00",
            object_class="sun",
            object_id="sun",
            event_type="astronomical_dawn",
            altitude=-18.0,
        ),
        _row(
            utc="2026-01-01T11:00:00+00:00",
            local="2026-01-01T21:00:00+10:00",
            object_class="moon",
            object_id="moon",
            event_type="rise",
            altitude=-0.8392,
        ),
    ]

    twilight, _phases, moon = generate_sun_moon_tables(2026, site, events)

    assert twilight[0]["dusk_astronomical_local"] == "2026-01-01T19:00:00+10:00"
    assert twilight[0]["dawn_astronomical_local"] == "2026-01-01T04:00:00+10:00"
    assert moon[0]["moonrise_local"] == "2026-01-01T21:00:00+10:00"
    assert moon[0]["moonset_local"] == ""


def test_csv_schema_keeps_second_precision(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    row = _row(
        utc="2026-01-01T09:00:17+00:00",
        local="2026-01-01T19:00:17+10:00",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)

    with path.open(encoding="utf-8", newline="") as handle:
        loaded = next(csv.DictReader(handle))

    assert datetime.fromisoformat(loaded["event_time_utc"]).astimezone(UTC).second == 17
