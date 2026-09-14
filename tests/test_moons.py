from paa.compute.moons import _wrap_delta_ra_deg


def test_wrap_delta_ra_deg_wraps_across_zero() -> None:
    assert round(_wrap_delta_ra_deg(1.0, 359.0), 3) == 2.0
    assert round(_wrap_delta_ra_deg(359.0, 1.0), 3) == -2.0
