import csv
from html.parser import HTMLParser
from importlib import resources
from pathlib import Path

from paa.render.html import render_annual_html, render_landing_html


class _LandmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.ids.update(value for key, value in attrs if key == "id" and value is not None)


def _render_fixture(tmp_path: Path) -> Path:
    data = tmp_path / "output" / "se_qld" / "2027" / "data"
    data.mkdir(parents=True)
    with (data / "sun_twilight.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "dusk_astronomical_local", "dawn_astronomical_local"])
        writer.writerow(["2027-01-01", "2027-01-01T19:14:00+10:00", "2027-01-01T04:28:00+10:00"])
    return render_annual_html(2027, "se_qld", tmp_path / "output")


def test_exact_identity_and_semantic_landmarks_are_rendered(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    html = annual.read_text(encoding="utf-8")

    assert "नभस्तल" in html
    assert "Nabhastala" in html
    assert "त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)" in html
    assert "One sky at three horizons." in html
    assert 'lang="sa-Deva"' in html
    assert 'href="#main-content"' in html

    parser = _LandmarkParser()
    parser.feed(html)
    assert {"header", "nav", "main", "footer", "table", "caption"}.issubset(parser.tags)
    assert "main-content" in parser.ids

    devanagari = html.index('<span class="identity__devanagari"')
    sanskrit = html.index('<span class="identity__sanskrit"')
    translation = html.index('<span class="identity__translation"')
    english = html.index('<span class="identity__english"')
    assert devanagari < sanskrit < translation < english


def test_monthly_pages_use_relative_assets_and_work_without_javascript(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    january = annual.parent / "months" / "01.html"
    html = january.read_text(encoding="utf-8")

    assert '../assets/styles.css' in html
    assert '../assets/theme.js' in html
    assert 'href="../almanac.html"' in html
    assert 'href="../data/index.html"' in html
    assert "Sun and twilight" in html
    assert "1 Jan 2027" in html
    assert len(list((annual.parent / "months").glob("*.html"))) == 12


def test_packaged_assets_cover_theme_accessibility_print_and_local_fonts(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    assets = annual.parent / "assets"
    css = (assets / "styles.css").read_text(encoding="utf-8")
    script = (assets / "theme.js").read_text(encoding="utf-8")

    assert ':root[data-theme="dark"]' in css
    assert "prefers-color-scheme: dark" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ":focus-visible" in css
    assert "@media print" in css
    assert "fonts.googleapis.com" not in css
    assert "nabhastala-theme" in script
    assert (assets / "fonts" / "atkinson-regular-latin.woff2").read_bytes()[:4] == b"wOF2"
    assert (assets / "fonts" / "noto-sans-devanagari.woff2").read_bytes()[:4] == b"wOF2"


def test_templates_and_static_assets_are_package_resources() -> None:
    package = resources.files("paa.render")
    assert package.joinpath("templates", "annual.html").is_file()
    assert package.joinpath("templates", "monthly.html").is_file()
    assert package.joinpath("templates", "landing.html").is_file()
    assert package.joinpath("templates", "data_library.html").is_file()
    assert package.joinpath("static", "styles.css").is_file()


def test_landing_page_lists_horizons_and_available_local_editions(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    landing = annual.parents[2] / "index.html"
    html = landing.read_text(encoding="utf-8")

    assert landing == render_landing_html(tmp_path / "output")
    assert "South East Queensland, Australia" in html
    assert "Southern Tasmania, Australia" in html
    assert "Malabar Coast, India" in html
    assert 'href="se_qld/2027/almanac.html"' in html
    assert "No local edition generated yet." in html
    assert "<table" not in html
    assert 'href="#horizons"' in html


def test_data_library_links_complete_csv_without_rendering_its_rows(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    library = annual.parent / "data" / "index.html"
    html = library.read_text(encoding="utf-8")

    assert library.exists()
    assert "Sun and twilight" in html
    assert "1 records" in html
    assert 'href="sun_twilight.csv" download' in html
    assert "2027-01-01T19:14:00+10:00" not in html
    assert 'href="../almanac.html"' in html
    assert 'href="../../../index.html"' in html
