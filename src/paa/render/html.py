from __future__ import annotations

import csv
from html import escape
from pathlib import Path


SECTIONS = [
    ("sun_twilight.csv", "Sun/Twilight"),
    ("moon_phase.csv", "Moon Phase/Illumination"),
    ("moonrise_moonset.csv", "Moonrise/Moonset"),
    ("moon_dark_windows.csv", "Moon-Free Dark Windows"),
    ("milky_way_windows.csv", "Milky Way Core Visibility"),
    ("milky_way_monthly_summary.csv", "Milky Way Monthly Summary"),
    ("planet_visibility_daily.csv", "Planet Visibility Daily"),
    ("planet_visibility_monthly_summary.csv", "Planet Visibility Monthly Summary"),
    ("jupiter_moons.csv", "Jupiter Moons Relative Offsets"),
    ("saturn_moons.csv", "Saturn Moons Relative Offsets"),
    ("minor_planets.csv", "Minor Planet Opportunities"),
    ("comets.csv", "Comet Opportunities"),
    ("lunar_occultations.csv", "Lunar Occultations"),
    ("meteor_showers.csv", "Meteor Showers"),
]


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _table(headers: list[str], rows: list[list[str]], max_rows: int | None = None) -> str:
    if not headers:
        return "<p>No data.</p>"
    body = rows if max_rows is None else rows[:max_rows]
    thead = "".join(f"<th>{escape(h)}</th>" for h in headers)
    tbody = ""
    for r in body:
        cells = "".join(f"<td>{escape(c)}</td>" for c in r)
        tbody += f"<tr>{cells}</tr>"
    return f"<table border='1' cellspacing='0' cellpadding='4'><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def _month_filter(headers: list[str], rows: list[list[str]], month: int) -> list[list[str]]:
    if not headers:
        return []
    idx = None
    for c in ["date", "month", "peak_date_local", "best_date", "datetime_local"]:
        if c in headers:
            idx = headers.index(c)
            break
    if idx is None:
        return rows
    out = []
    for r in rows:
        if idx >= len(r):
            continue
        v = r[idx]
        if len(v) >= 7 and v[5:7].isdigit() and int(v[5:7]) == month:
            out.append(r)
    return out


def render_annual_html(year: int, site_id: str, output_dir: Path) -> Path:
    year_dir = output_dir / str(year)
    data_dir = year_dir / "data"
    months_dir = year_dir / "months"
    months_dir.mkdir(parents=True, exist_ok=True)

    for m in range(1, 13):
        chunks = [f"<h1>{year}-{m:02d} Monthly Almanac</h1>"]
        chunks.append(f"<p><a href='../almanac.html'>Back to annual index</a></p>")
        for fname, title in SECTIONS:
            h, r = _read_csv(data_dir / fname)
            mr = _month_filter(h, r, m)
            chunks.append(f"<h2>{escape(title)}</h2>")
            chunks.append(_table(h, mr, max_rows=200))
        page = "<!doctype html><html><head><meta charset='utf-8'><title>Monthly Almanac</title></head><body>" + "".join(chunks) + "</body></html>"
        (months_dir / f"{m:02d}.html").write_text(page, encoding="utf-8")

    sections_html = []
    for fname, title in SECTIONS:
        h, r = _read_csv(data_dir / fname)
        sections_html.append(f"<h2>{escape(title)}</h2>")
        sections_html.append(_table(h, r, max_rows=None))

    month_links = " ".join([f"<a href='months/{m:02d}.html'>{m:02d}</a>" for m in range(1, 13)])
    charts_html = ""
    for rel in ["charts/milky_way_windows.png", "charts/jupiter_moons/strip_chart.png", "charts/saturn_moons/strip_chart.png"]:
        p = year_dir / rel
        if p.exists():
            charts_html += f"<h2>{escape(Path(rel).name)}</h2><img src='{rel}' style='max-width:100%;height:auto;'/>"

    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='author' content='Prajwal Bhattaram'>"
        "<meta name='generator' content='personal-astro-almanac'>"
        f"<title>Personal Astro Almanac {year}</title></head><body>"
        f"<h1>Personal Astro Almanac {year}</h1><p>Site: {escape(site_id)}</p>"
        f"<p>Monthly pages: {month_links}</p>"
        + "".join(sections_html)
        + charts_html
        + "</body></html>"
    )

    out = year_dir / "almanac.html"
    out.write_text(html, encoding="utf-8")
    return out


def render_milestone1_html(year: int, site_id: str, output_dir: Path) -> Path:
    return render_annual_html(year=year, site_id=site_id, output_dir=output_dir)
