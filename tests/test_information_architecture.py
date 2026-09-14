import csv
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from paa.render.html import render_annual_html

FIXTURE = Path(__file__).parent / "fixtures" / "stage1_almanac.json"
SITES = ("se_qld", "southern_tasmania", "malabar_coast")


class _DocumentLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        attribute = "src" if tag in {"img", "script"} else "href"
        if values.get(attribute):
            self.references.append(values[attribute] or "")


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _write_fixture(data_dir: Path) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data_dir.mkdir(parents=True)
    for filename, table in fixture.items():
        rows = table["rows"]
        if table.get("repeat_to"):
            rows = [rows[0] for _ in range(table["repeat_to"])]
        with (data_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(table["headers"])
            writer.writerows(rows)


def _build_three_site_fixture(output: Path) -> None:
    for site_id in SITES:
        _write_fixture(output / site_id / "2027" / "data")
        render_annual_html(2027, site_id, output)


def test_all_local_links_assets_and_fragment_targets_resolve(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _build_three_site_fixture(output)

    for document in output.rglob("*.html"):
        parser = _DocumentLinks()
        parser.feed(document.read_text(encoding="utf-8"))
        assert len(parser.ids) == len(set(parser.ids)), f"duplicate id in {document}"
        for reference in parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc:
                continue
            if not parsed.path:
                assert parsed.fragment in parser.ids, (document, reference)
                continue
            target = (document.parent / unquote(parsed.path)).resolve()
            assert target.exists(), (document, reference)
            if parsed.fragment and target.suffix == ".html":
                target_parser = _DocumentLinks()
                target_parser.feed(target.read_text(encoding="utf-8"))
                assert parsed.fragment in target_parser.ids, (document, reference)


def test_three_sites_coexist_and_landing_links_each_edition(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _build_three_site_fixture(output)
    landing = (output / "index.html").read_text(encoding="utf-8")

    for site_id in SITES:
        edition = output / site_id / "2027" / "almanac.html"
        assert edition.exists()
        assert f'href="{site_id}/2027/almanac.html"' in landing
        html = edition.read_text(encoding="utf-8")
        assert f">{site_id}</dd>" in html
        assert all(f"/{other}/" not in html for other in SITES if other != site_id)


def test_core_views_need_no_javascript_and_reflow_rules_are_scoped(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_fixture(output / "se_qld" / "2027" / "data")
    annual = render_annual_html(2027, "se_qld", output)
    month = annual.parent / "months" / "01.html"
    css = (annual.parent / "assets" / "styles.css").read_text(encoding="utf-8")

    annual_html = annual.read_text(encoding="utf-8")
    month_html = month.read_text(encoding="utf-8")
    assert "Year at a glance" in annual_html
    assert "Night-planning overview" in month_html
    assert "<noscript" not in annual_html + month_html
    assert 'class="js-only"' not in annual_html + month_html
    assert "min-width: 20rem" not in css
    assert "@media (max-width: 52rem)" in css
    assert "@media (max-width: 36rem)" in css
    assert "overflow-x: auto" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ":focus-visible" in css


def test_light_and_dark_text_tokens_meet_normal_text_contrast() -> None:
    light_background = "#f4efe5"
    dark_background = "#181b1f"
    for foreground in ("#29251f", "#655e52", "#9b5849"):
        assert _contrast(foreground, light_background) >= 4.5
    for foreground in ("#ebe5d6", "#b6ae9d", "#d7ccb2"):
        assert _contrast(foreground, dark_background) >= 4.5


def test_data_library_groups_files_and_discloses_schema_without_rows(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _write_fixture(output / "se_qld" / "2027" / "data")
    annual = render_annual_html(2027, "se_qld", output)
    html = (annual.parent / "data" / "index.html").read_text(encoding="utf-8")

    assert "Night planning" in html
    assert "Deep sky" in html
    assert "Planets and satellites" in html
    assert "Events and targets" in html
    assert "Supporting and provenance" not in html
    assert "File details" in html
    assert "<details>" in html
    assert "<summary>File details</summary>" in html
    assert "Dusk astronomical local" in html
    assert "2027-01-01T19:14:00+10:00" not in html
    assert "<script>unsafe</script>" not in html
    assert 'href="comets.csv" download' in html
