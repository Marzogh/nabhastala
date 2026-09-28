from pathlib import Path

import pytest

from paa.compute.phenomena import (
    circle_overlap_fraction,
    compute_astronomical_phenomena,
)


def test_circle_overlap_fraction_handles_clear_total_and_partial_cases() -> None:
    assert circle_overlap_fraction(1.0, 1.0, 2.1) == 0.0
    assert circle_overlap_fraction(1.0, 2.0, 0.5) == 1.0
    assert circle_overlap_fraction(1.0, 1.0, 1.0) == pytest.approx(0.391, abs=0.001)


def test_2026_phenomena_include_known_eclipses_and_opposition(
    tmp_path: Path,
) -> None:
    source_cache = Path("output/_sources/occultations")
    rows = compute_astronomical_phenomena(
        year=2026,
        latitude_deg=-27.5,
        longitude_deg=153.0,
        elevation_m=50,
        timezone_name="Australia/Brisbane",
        source_cache=source_cache if source_cache.exists() else tmp_path,
    )

    events = {(row["target"], row["event"]): row for row in rows}
    assert ("Moon", "Total lunar eclipse") in events
    assert ("Moon", "Partial lunar eclipse") in events
    assert ("Jupiter", "Opposition") in events
    assert any("elongation" in row["event"] for row in rows)
    assert any(row["event"] == "Stationary point" for row in rows)
    assert events[("Moon", "Total lunar eclipse")]["datetime_local"].startswith(
        "2026-03-03"
    )
