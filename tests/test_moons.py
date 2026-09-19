from paa.compute.moons import _best_dates, _wrap_delta_ra_deg


def test_wrap_delta_ra_deg_wraps_across_zero() -> None:
    assert round(_wrap_delta_ra_deg(1.0, 359.0), 3) == 2.0
    assert round(_wrap_delta_ra_deg(359.0, 1.0), 3) == -2.0


def test_best_dates_are_observable_and_spread_across_months() -> None:
    rows = [
        {
            "planet": "Jupiter",
            "date": "2027-01-01",
            "best_time_local": "x",
            "visibility_rating": "excellent",
            "max_altitude_deg": "70",
        },
        {
            "planet": "Jupiter",
            "date": "2027-01-02",
            "best_time_local": "x",
            "visibility_rating": "excellent",
            "max_altitude_deg": "69",
        },
        {
            "planet": "Jupiter",
            "date": "2027-02-01",
            "best_time_local": "x",
            "visibility_rating": "good",
            "max_altitude_deg": "55",
        },
        {
            "planet": "Jupiter",
            "date": "2027-03-01",
            "best_time_local": "",
            "visibility_rating": "excellent",
            "max_altitude_deg": "80",
        },
    ]

    assert _best_dates(rows, "Jupiter", top_n=3) == ["2027-01-01", "2027-02-01"]
