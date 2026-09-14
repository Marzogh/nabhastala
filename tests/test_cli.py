from paa.cli import build_parser


def test_help() -> None:
    parser = build_parser()
    assert parser.prog == "astro-almanac"


def test_build_has_database_url_arg() -> None:
    parser = build_parser()
    args = parser.parse_args(["build", "--year", "2027", "--site", "se_qld", "--database-url", "postgresql://x/y"])
    assert args.database_url == "postgresql://x/y"
