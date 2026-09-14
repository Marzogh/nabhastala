import csv
from pathlib import Path

from paa.render.almanac_views import build_month_guide
from paa.render.html import render_annual_html


def _write(data_dir: Path, filename: str, rows: list[dict[str, object]]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / filename).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(data_dir: Path) -> None:
    _write(
        data_dir,
        "sun_twilight.csv",
        [{
            "date": "2027-01-15",
            "dusk_astronomical_local": "2027-01-15T19:20:00+10:00",
            "dawn_astronomical_local": "2027-01-15T04:30:00+10:00",
        }],
    )
    _write(
        data_dir,
        "moon_phase.csv",
        [
            {"date": "2027-01-01", "moon_illumination_fraction": 0.96},
            {"date": "2027-01-15", "moon_illumination_fraction": 0.02},
        ],
    )
    _write(
        data_dir,
        "moon_dark_windows.csv",
        [
            {
                "date": "2027-01-15",
                "start_local": "2027-01-15T20:00:00+10:00",
                "end_local": "2027-01-16T04:00:00+10:00",
                "duration_minutes": 480,
                "moon_illumination_fraction": 0.02,
            },
            {
                "date": "2027-01-16",
                "start_local": "2027-01-16T21:00:00+10:00",
                "end_local": "2027-01-17T03:00:00+10:00",
                "duration_minutes": 360,
                "moon_illumination_fraction": 0.05,
            },
        ],
    )
    _write(
        data_dir,
        "milky_way_windows.csv",
        [{
            "date": "2027-01-15",
            "start_local": "2027-01-15T02:00:00+10:00",
            "end_local": "2027-01-15T04:00:00+10:00",
            "duration_minutes": 120,
            "max_altitude_deg": 48,
            "quality": "excellent",
        }],
    )
    _write(
        data_dir,
        "planet_visibility_monthly_summary.csv",
        [
            {"month": "2027-01", "planet": "Jupiter", "best_date": "2027-01-10", "best_altitude_deg": 60, "rating": "good"},
            {"month": "2027-01", "planet": "Mars", "best_date": "2027-01-11", "best_altitude_deg": 70, "rating": "excellent"},
        ],
    )
    _write(
        data_dir,
        "planet_visibility_daily.csv",
        [
            {"date": "2027-01-10", "planet": "Jupiter", "twilight_best_time_local": "2027-01-10T19:30:00+10:00", "twilight_max_altitude_deg": 40},
            {"date": "2027-01-11", "planet": "Mars", "twilight_best_time_local": "2027-01-11T19:30:00+10:00", "twilight_max_altitude_deg": -2},
        ],
    )
    _write(
        data_dir,
        "meteor_showers.csv",
        [{
            "id": "quadrantids",
            "name": "Quadrantids",
            "peak_date_local": "2027-01-03",
            "radiant_alt_predawn_deg": 18,
            "moon_illumination_fraction": 0.9,
            "score": 1,
            "rating": "poor",
        }],
    )
    _write(
        data_dir,
        "comets.csv",
        [{
            "target": "10P",
            "best_datetime_local": "",
            "best_altitude_deg": "",
            "best_apmag": "",
            "rating": "query_failed",
            "amateur_chaseable": "False",
            "calc_status": "query_failed",
        }],
    )


def test_month_guide_selects_field_information_without_recalculating_scores(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _fixture(data_dir)

    guide = build_month_guide(2027, 1, "se_qld", data_dir)

    assert guide.new_moon_date == "2027-01-15"
    assert guide.full_moon_date == "2027-01-01"
    assert guide.dark_windows[0].duration_minutes == 480
    assert guide.milky_way_sessions[0].max_altitude_deg == 48
    assert guide.planet_groups[0].period == "Evening"
    assert [planet.planet for planet in guide.planet_groups[0].planets] == ["Jupiter"]
    assert any("comet calculations are unavailable" in note for note in guide.data_notes)
    assert all(item.category != "Comets" for item in guide.highlights)


def test_rendered_month_is_a_field_guide_with_contextual_downloads(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _fixture(output / "se_qld" / "2027" / "data")

    annual = render_annual_html(2027, "se_qld", output)
    html = (annual.parent / "months" / "01.html").read_text(encoding="utf-8")

    assert "The month in one sentence" in html
    assert "Astronomical dusk" in html
    assert "Recommended core sessions" in html
    assert "Useful at twilight" in html
    assert 'href="../data/moon_dark_windows.csv" download' in html
    assert "query_failed" not in html
    assert "<table" not in html
