from paa.compute.planets import _rating


def test_planet_rating_thresholds() -> None:
    assert _rating(50, excellent_alt=45, min_alt=25) == "excellent"
    assert _rating(30, excellent_alt=45, min_alt=25) == "good"
    assert _rating(20, excellent_alt=45, min_alt=25) == "fair"
