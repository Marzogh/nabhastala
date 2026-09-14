from __future__ import annotations

import calendar
import csv
import re
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from paa.paths import resolve_site_year_dir, site_year_dir
from paa.render.view_models import format_display_value, humanize_label, rating_tone

SECTIONS = [
    ("sun_twilight.csv", "Sun and twilight"),
    ("moon_phase.csv", "Moon phase and illumination"),
    ("moonrise_moonset.csv", "Moonrise and moonset"),
    ("moon_dark_windows.csv", "Moon-free dark windows"),
    ("milky_way_windows.csv", "Milky Way core visibility"),
    ("milky_way_monthly_summary.csv", "Milky Way monthly summary"),
    ("planet_visibility_daily.csv", "Daily planet visibility"),
    ("planet_visibility_monthly_summary.csv", "Monthly planet visibility"),
    ("jupiter_moons.csv", "Jupiter moon offsets"),
    ("saturn_moons.csv", "Saturn moon offsets"),
    ("minor_planets.csv", "Minor planet opportunities"),
    ("comets.csv", "Comet opportunities"),
    ("lunar_occultations.csv", "Lunar occultations"),
    ("meteor_showers.csv", "Meteor showers"),
]

CHARTS = [
    ("charts/milky_way_windows.png", "Milky Way visibility through the year"),
    ("charts/jupiter_moons/strip_chart.png", "Jupiter moon relative offsets"),
    ("charts/saturn_moons/strip_chart.png", "Saturn moon relative offsets"),
]

SITE_NAMES = {
    "se_qld": "South East Queensland, Australia",
    "southern_tasmania": "Southern Tasmania, Australia",
    "malabar_coast": "Malabar Coast, India",
}


@dataclass(frozen=True)
class TableView:
    title: str
    section_id: str
    headers: list[str]
    rows: list[list[str]]
    total_rows: int
    truncated: bool


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _month_filter(headers: list[str], rows: list[list[str]], month: int) -> list[list[str]]:
    if not headers:
        return []
    index = None
    for candidate in ("date", "month", "peak_date_local", "best_date", "datetime_local"):
        if candidate in headers:
            index = headers.index(candidate)
            break
    if index is None:
        return rows
    return [
        row
        for row in rows
        if index < len(row)
        and len(row[index]) >= 7
        and row[index][5:7].isdigit()
        and int(row[index][5:7]) == month
    ]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _table_view(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    max_rows: int | None = None,
) -> TableView:
    selected = rows if max_rows is None else rows[:max_rows]
    display_rows = [
        [
            format_display_value(headers[index], value) if index < len(headers) else str(value)
            for index, value in enumerate(row)
        ]
        for row in selected
    ]
    return TableView(
        title=title,
        section_id=_slug(title),
        headers=[humanize_label(header) for header in headers],
        rows=display_rows,
        total_rows=len(rows),
        truncated=len(selected) < len(rows),
    )


def _environment() -> Environment:
    environment = Environment(
        loader=PackageLoader("paa.render", "templates"),
        autoescape=select_autoescape(("html", "xml")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.globals["rating_tone"] = rating_tone
    return environment


def _copy_static_assets(year_dir: Path) -> None:
    static = resources.files("paa.render").joinpath("static")
    with resources.as_file(static) as static_path:
        shutil.copytree(static_path, year_dir / "assets", dirs_exist_ok=True)


def _copy_charts(source_year_dir: Path, year_dir: Path) -> list[dict[str, str]]:
    charts: list[dict[str, str]] = []
    for relative, alt in CHARTS:
        source = source_year_dir / relative
        if not source.exists():
            continue
        target = year_dir / relative
        if source != target:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        charts.append({"src": relative, "alt": alt, "title": alt})
    return charts


def render_annual_html(year: int, site_id: str, output_dir: Path) -> Path:
    year_dir = site_year_dir(output_dir, site_id, year)
    source_year_dir = resolve_site_year_dir(output_dir, site_id, year, required="data")
    data_dir = source_year_dir / "data"
    months_dir = year_dir / "months"
    months_dir.mkdir(parents=True, exist_ok=True)
    _copy_static_assets(year_dir)

    source_tables = [
        (filename, title, *_read_csv(data_dir / filename)) for filename, title in SECTIONS
    ]
    month_links = [
        {
            "number": month,
            "label": calendar.month_abbr[month],
            "href": f"months/{month:02d}.html",
        }
        for month in range(1, 13)
    ]
    common = {
        "year": year,
        "site_id": site_id,
        "site_name": SITE_NAMES.get(site_id, humanize_label(site_id)),
        "identity_devanagari": "नभस्तल",
        "identity_english": "Nabhastala",
        "motto_sanskrit": "त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)",
        "motto_english": "One sky at three horizons.",
    }
    environment = _environment()

    for month in range(1, 13):
        tables = [
            _table_view(title, headers, _month_filter(headers, rows, month), max_rows=200)
            for _, title, headers, rows in source_tables
        ]
        page = environment.get_template("monthly.html").render(
            **common,
            document_title=f"{calendar.month_name[month]} {year} — Nabhastala",
            page_title=f"{calendar.month_name[month]} {year}",
            page_eyebrow="Monthly field almanac",
            page_description=f"Observing reference for {common['site_name']}.",
            tables=tables,
            month_links=[
                {**item, "href": f"{item['number']:02d}.html"} for item in month_links
            ],
            active_month=month,
            annual_href="../almanac.html",
            asset_prefix="../assets/",
        )
        (months_dir / f"{month:02d}.html").write_text(page, encoding="utf-8")

    annual_tables = [
        _table_view(title, headers, rows) for _, title, headers, rows in source_tables
    ]
    charts = _copy_charts(source_year_dir, year_dir)
    annual = environment.get_template("annual.html").render(
        **common,
        document_title=f"Nabhastala — {year} field almanac",
        page_title=f"{year} field almanac",
        page_eyebrow="Annual observing reference",
        page_description=(
            f"A complete astronomy and astrophotography reference for {common['site_name']}."
        ),
        tables=annual_tables,
        charts=charts,
        month_links=month_links,
        active_month=None,
        annual_href="almanac.html",
        asset_prefix="assets/",
    )
    output = year_dir / "almanac.html"
    output.write_text(annual, encoding="utf-8")
    return output


def render_milestone1_html(year: int, site_id: str, output_dir: Path) -> Path:
    return render_annual_html(year=year, site_id=site_id, output_dir=output_dir)
