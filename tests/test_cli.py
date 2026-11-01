from pathlib import Path

from paa.cli import _write_csv, build_parser


def test_help() -> None:
    parser = build_parser()
    assert parser.prog == "astro-almanac"


def test_build_has_database_url_arg() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["build", "--year", "2027", "--site", "se_qld", "--database-url", "postgresql://x/y"]
    )
    assert args.database_url == "postgresql://x/y"


def test_view_keeps_shorthand_and_defaults_to_primary_site() -> None:
    parser = build_parser()
    args = parser.parse_args(["view", "--2027"])
    assert args.year == 2027
    assert args.site == "se_qld"


def test_annual_release_defaults_to_all_configured_sites() -> None:
    parser = build_parser()
    args = parser.parse_args(["annual-release", "--year", "2028"])

    assert args.year == 2028
    assert args.sites == "all"
    assert args.sections == "all"


def test_write_csv_uses_lf_line_endings(tmp_path: Path) -> None:
    output = tmp_path / "rows.csv"

    _write_csv(output, [{"name": "Sun", "event": "rise"}])

    assert output.read_bytes() == b"name,event\nSun,rise\n"
