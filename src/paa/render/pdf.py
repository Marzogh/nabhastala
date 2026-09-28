from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from paa.paths import public_site_slug, resolve_site_year_dir
from paa.render.almanac_views import (
    build_annual_overview,
    build_month_guide,
    build_observing_instruments,
)
from paa.render.html import SITE_NAMES, _environment


def _pdf_filename(year: int, site_id: str) -> str:
    return f"nabhastala-{year}-{public_site_slug(site_id)}-field-edition.pdf"


def render_pdf_from_html(html_path: Path, pdf_path: Path) -> Path:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("weasyprint")
    if executable:
        font_cache = Path("tmp/font-cache").resolve()
        font_cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [executable, str(html_path), str(pdf_path)],
            check=True,
            text=True,
            env={**os.environ, "XDG_CACHE_HOME": str(font_cache)},
        )
        return pdf_path

    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PDF rendering requires the WeasyPrint command or Python package."
        ) from exc
    HTML(filename=str(html_path), base_url=str(html_path.parent)).write_pdf(str(pdf_path))
    return pdf_path


def render_field_pdf(year: int, site_id: str, output_dir: Path) -> Path:
    """Render a curated, technical field edition from reviewed local data."""
    source_year_dir = resolve_site_year_dir(output_dir, site_id, year, required="data")
    data_dir = source_year_dir / "data"
    overview = build_annual_overview(year, site_id, data_dir)
    guides = tuple(build_month_guide(year, month, site_id, data_dir) for month in range(1, 13))
    instruments = build_observing_instruments(year, data_dir)

    intermediate_dir = Path("tmp/pdfs")
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    html_path = intermediate_dir / f"{year}-{site_id}-field-edition.html"
    css_path = Path(__file__).with_name("static") / "field_pdf.css"

    page = _environment().get_template("field_pdf.html").render(
        document_title=f"Nabhastala {year} field edition",
        identity_devanagari="नभस्तल",
        identity_english="Nabhastala",
        motto_sanskrit="त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)",
        motto_english="One sky at three horizons.",
        year=year,
        site_id=site_id,
        site_slug=public_site_slug(site_id),
        site_name=SITE_NAMES.get(site_id, site_id.replace("_", " ").title()),
        overview=overview,
        guides=guides,
        milky_instrument=instruments["milky_way"],
        css_uri=css_path.resolve().as_uri(),
        data_page="data/index.html",
    )
    html_path.write_text(page, encoding="utf-8")

    pdf_path = output_dir / "pdf" / _pdf_filename(year, site_id)
    return render_pdf_from_html(html_path, pdf_path)
