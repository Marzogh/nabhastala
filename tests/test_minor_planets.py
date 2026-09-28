from pathlib import Path

from paa.compute import minor_planets
from paa.compute.minor_planets import _score_row, compute_minor_planets_and_comets


def test_score_row_prefers_bright_high_alt_high_elong() -> None:
    score, rating = _score_row(apmag=7.5, altitude=55, solar_elong=120)
    assert score >= 5
    assert rating == "excellent"


def test_comets_use_current_solution_and_preserve_missing_magnitude(
    tmp_path: Path, monkeypatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "almanac.yaml").write_text(
        "minor_planets:\n  candidates: []\ncomets:\n  candidates: []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        minor_planets,
        "query_comet_candidates",
        lambda **kwargs: [{"pdes": "10P"}],
    )
    calls: list[dict] = []

    def fake_best_for_target(**kwargs):
        calls.append(kwargs)
        return {
            "target": "10P",
            "best_datetime_utc": "2026-01-01T12:00:00",
            "best_datetime_local": "2026-01-01T22:00:00+10:00",
            "best_altitude_deg": 55.0,
            "best_apmag": "",
            "solar_elong_deg": 90.0,
            "score": 0,
            "rating": "unavailable",
        }

    monkeypatch.setattr(minor_planets, "_best_for_target", fake_best_for_target)

    _, comets = compute_minor_planets_and_comets(
        year=2026,
        site_lat=-27.5,
        site_lon=153.1,
        site_elev=30,
        timezone_name="Australia/Brisbane",
        config_dir=config_dir,
        cache_dir=tmp_path / "cache",
    )

    assert calls[0]["command"] == "DES=10P;CAP"
    assert calls[0]["permit_missing_magnitude"] is True
    assert calls[0]["cache_path"].parent.name == "comets"
    assert comets[0]["calc_status"] == "magnitude_unavailable"
    assert comets[0]["amateur_chaseable"] is False
