from pathlib import Path

from paa.sources.occult_import import import_occult_file, score_occultation


def test_score_occultation_planetary_dark_limb() -> None:
    event = {
        "is_planetary": True,
        "target_mag": 0.5,
        "moon_altitude_deg": 35.0,
        "limb": "dark",
    }
    cfg = {"min_moon_altitude_deg": 10, "max_star_mag_imaging": 11, "max_star_mag_visual": 8}
    assert score_occultation(event, cfg) in {"good", "excellent"}


def test_import_occult_file_parses_basic_csv(tmp_path: Path) -> None:
    p = tmp_path / "occult.csv"
    p.write_text(
        "datetime,object,mag,moon alt,limb,type\n"
        "2027-05-01 20:15,Jupiter,-2.1,45,dark,planetary\n",
        encoding="utf-8",
    )
    rows = import_occult_file(p, timezone_name="Australia/Brisbane", cfg={"min_moon_altitude_deg": 10})
    assert len(rows) == 1
    assert rows[0]["target"] == "Jupiter"
    assert rows[0]["is_planetary"] is True
