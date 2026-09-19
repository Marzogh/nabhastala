from paa.compute.planets import _best_observable_index, _rating


def test_planet_rating_thresholds() -> None:
    assert _rating(50, excellent_alt=45, min_alt=25) == "excellent"
    assert _rating(30, excellent_alt=45, min_alt=25) == "good"
    assert _rating(20, excellent_alt=45, min_alt=25) == "fair"


def test_best_observable_index_rejects_daytime_altitude_maximum() -> None:
    altitudes = [22.0, 86.0, 41.0, 18.0]
    sun_altitudes = [-8.0, 35.0, -5.0, -18.0]

    assert _best_observable_index(altitudes, sun_altitudes) == 2
