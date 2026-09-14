import pytest

from paa.sources.horizons import parse_horizons_csv


def test_parse_horizons_csv_happy_path() -> None:
    raw = "header\n$$SOE\n2027-Jan-01 00:00,1,2,3\n2027-Jan-01 01:00,4,5,6\n$$EOE\n"
    rows = parse_horizons_csv(raw)
    assert len(rows) == 2
    assert rows[0][0] == "2027-Jan-01 00:00"


def test_parse_horizons_csv_missing_markers() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_horizons_csv("no markers")
