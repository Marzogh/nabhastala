from paa.compute.minor_planets import _score_row


def test_score_row_prefers_bright_high_alt_high_elong() -> None:
    score, rating = _score_row(apmag=7.5, altitude=55, solar_elong=120)
    assert score >= 5
    assert rating == "excellent"
