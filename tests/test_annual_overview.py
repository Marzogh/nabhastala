import csv
from pathlib import Path

import pytest

from paa.render.almanac_views import (
    build_annual_overview,
    rank_diverse_opportunities,
)


def _write_csv(data_dir: Path, filename: str, rows: list[dict[str, object]]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / filename).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_overview_fixture(data_dir: Path) -> None:
    _write_csv(
        data_dir,
        "moon_phase.csv",
        [
            {"date": "2027-01-01", "moon_illumination_fraction": 0.4},
            {"date": "2027-01-02", "moon_illumination_fraction": 0.05},
        ],
    )
    _write_csv(
        data_dir,
        "moon_dark_windows.csv",
        [
            {"date": "2027-01-02", "duration_minutes": 180},
            {"date": "2027-01-03", "duration_minutes": 260},
        ],
    )
    _write_csv(
        data_dir,
        "milky_way_monthly_summary.csv",
        [{"month": "2027-01", "window_count": 4, "excellent_count": 2}],
    )
    _write_csv(
        data_dir,
        "milky_way_windows.csv",
        [
            {
                "date": "2027-01-07",
                "start_local": "2027-01-07T02:00:00+10:00",
                "end_local": "2027-01-07T04:00:00+10:00",
                "duration_minutes": 120,
                "max_altitude_deg": 72,
                "quality": "excellent",
            }
        ],
    )
    _write_csv(
        data_dir,
        "planet_visibility_monthly_summary.csv",
        [
            {
                "month": "2027-01",
                "planet": "Jupiter",
                "best_date": "2027-01-10",
                "best_altitude_deg": 61,
                "rating": "excellent",
            },
            {
                "month": "2027-02",
                "planet": "Jupiter",
                "best_date": "2027-02-10",
                "best_altitude_deg": 42,
                "rating": "good",
            },
        ],
    )
    _write_csv(
        data_dir,
        "meteor_showers.csv",
        [
            {
                "id": "geminids",
                "name": "Geminids",
                "peak_date_local": "2027-12-14",
                "radiant_alt_predawn_deg": 35,
                "moon_illumination_fraction": 0.2,
                "score": 4,
                "rating": "good",
            }
        ],
    )
    _write_csv(
        data_dir,
        "minor_planets.csv",
        [
            {
                "target": "4;",
                "best_datetime_local": "2027-11-05T22:00:00+10:00",
                "best_altitude_deg": 67,
                "best_apmag": 6.8,
                "score": 6,
                "rating": "excellent",
            }
        ],
    )
    _write_csv(
        data_dir,
        "comets.csv",
        [
            {
                "target": "10P",
                "best_datetime_local": "",
                "best_altitude_deg": "",
                "best_apmag": "",
                "score": 0,
                "rating": "query_failed",
                "amateur_chaseable": "False",
            }
        ],
    )


def test_annual_overview_selects_month_signals_and_diverse_complete_highlights(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_overview_fixture(data_dir)

    overview = build_annual_overview(2027, "se_qld", data_dir)

    assert len(overview.months) == 12
    january = overview.months[0]
    assert january.moon_illumination == 0.05
    assert january.best_dark_window == "3 Jan 2027 · 4h 20m"
    assert january.lead_category == "Milky Way"
    assert january.href == "months/01.html"
    assert {item.category for item in overview.highlights} == {
        "Milky Way",
        "Planets",
        "Meteor showers",
        "Minor planets",
    }
    assert all(item.category != "Comets" for item in overview.highlights)
    assert any(item.title == "Minor planet 4" for item in overview.highlights)
    assert overview.planet_seasons[0].best_date == "2027-01-10"


def test_diverse_ranking_validates_limit() -> None:
    assert rank_diverse_opportunities([], limit=0) == ()
    with pytest.raises(ValueError, match="limit"):
        rank_diverse_opportunities([], limit=-1)
