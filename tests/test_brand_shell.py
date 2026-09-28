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
    assert {"header", "nav", "main", "footer"}.issubset(parser.tags)
    assert "main-content" in parser.ids

    devanagari = html.index('<span class="identity__devanagari"')
    sanskrit = html.index('<span class="identity__sanskrit"')
    translation = html.index('<span class="identity__translation"')
    english = html.index('<span class="identity__english"')
    assert devanagari < sanskrit < translation < english


def test_annual_page_is_an_editorial_overview_not_a_dataset_dump(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    html = annual.read_text(encoding="utf-8")

    assert "Best observing opportunities" in html
    assert "Best observing opportunities in 2027" in html
    assert "Monthly guides" in html
    assert 'href="data/index.html"' in html
    assert html.count('class="month-card ') == 12
    assert 'src="assets/art/landscape-light.webp"' in html
    assert 'src="assets/art/planet-jupiter.png"' in html
    assert "<table" not in html
    assert "dataset-list" not in html


def test_monthly_pages_use_relative_assets_and_work_without_javascript(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    january = annual.parent / "months" / "01.html"
    html = january.read_text(encoding="utf-8")

    assert "../assets/styles.css" in html
    assert "../assets/editorial.css" in html
    assert "../assets/theme.js" in html
    assert "../assets/conditions.js" in html
    assert 'href="../almanac.html"' in html
    assert 'href="../data/index.html"' in html
    assert "The date selector requires JavaScript" in html
    assert ">Night planner<" in html
    assert "January highlights" in html
    assert ">Current conditions<" in html
    assert "Sky chart: 15 Jan 2027, 10 pm" in html
    assert 'href="../sky/index.html?date=2027-01-15&amp;time=22:00"' in html
    assert "Show static monthly chart" in html
    assert '<details class="monthly-sky-disclosure">' in html
    assert '<details class="monthly-sky-disclosure" open>' not in html
    assert 'src="../charts/sky/month-01.svg"' in html
    assert 'data-planet-icon-base="../assets/art"' in html
    assert "planetIcon" in (annual.parent / "assets" / "charts.js").read_text(
        encoding="utf-8"
    )
    assert (annual.parent / "charts" / "sky" / "month-01.svg").exists()
    for planet in ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"):
        assert (annual.parent / "assets" / "art" / f"planet-{planet}.png").exists()
    assert "1 Jan" in html
    assert "<table" not in html
    assert len(list((annual.parent / "months").glob("*.html"))) == 12


def test_sky_finder_is_linked_and_has_a_static_fallback(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    sky_page = annual.parent / "sky" / "index.html"
    html = sky_page.read_text(encoding="utf-8")

    assert 'href="sky/index.html"' in annual.read_text(encoding="utf-8")
    assert ">Night sky chart<" in html
    assert 'data-sky-date' in html
    assert 'data-sky-time' in html
    assert 'src="../assets/sky.js?v=monthly-sky-summary-1"' in html
    assert 'data-source="../assets/data/sky-data.json"' in html
    assert "URLSearchParams" in (annual.parent / "assets" / "sky.js").read_text(
        encoding="utf-8"
    )
    assert "<noscript>" in html
    assert (annual.parent / "assets" / "data" / "sky-data.json").exists()


def test_packaged_assets_cover_theme_accessibility_print_and_local_fonts(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    assets = annual.parent / "assets"
    css = (assets / "styles.css").read_text(encoding="utf-8")
    editorial = (assets / "editorial.css").read_text(encoding="utf-8")
    script = (assets / "theme.js").read_text(encoding="utf-8")

    assert ':root[data-theme="dark"]' in css
    assert "prefers-color-scheme: dark" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ":focus-visible" in css
    assert "@media print" in css
    assert "fonts.googleapis.com" not in css
    assert "theme-art--dark" in editorial
    assert ".planet-icon" in css
    assert "grayscale(1)" in css
    assert ".monthly-sky-disclosure:not([open]) > :not(summary) { display: none; }" in editorial
    assert ".monthly-sky-chart { max-width: 45rem;" in editorial
    assert sum(path.stat().st_size for path in (assets / "art").glob("*.webp")) < 800_000
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
    assert package.joinpath("static", "editorial.css").is_file()
    assert package.joinpath("static", "art", "landscape-light.webp").is_file()


def test_landing_page_lists_horizons_and_available_local_editions(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    landing = annual.parents[2] / "index.html"
    html = landing.read_text(encoding="utf-8")

    assert landing == render_landing_html(tmp_path / "output")
    assert "South East Queensland, Australia" in html
    assert "Southern Tasmania, Australia" in html
    assert "Malabar Coast, India" in html
    assert 'href="se_qld/2027/almanac.html"' in html
    assert "No edition is available yet." in html
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


def test_public_pages_avoid_promotional_and_process_language(tmp_path: Path) -> None:
    annual = _render_fixture(tmp_path)
    pages = (
        annual.parents[2] / "index.html",
        annual,
        annual.parent / "months" / "01.html",
        annual.parent / "data" / "index.html",
        annual.parent / "sky" / "index.html",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in pages)
    banned = (
        "A practical observing and nightscape planner",
        "Three locations. Local sky time.",
        "concise shortlist",
        "complete, observable records",
        "Highlights first",
        "What deserves attention",
        "Looking for an observing recommendation?",
        "locally generated moon data",
    )

    for phrase in banned:
        assert phrase not in combined
