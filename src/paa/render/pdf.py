from __future__ import annotations

from pathlib import Path


def render_pdf_from_html(html_path: Path, pdf_path: Path) -> Path:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF rendering requires weasyprint. Install with: pip install weasyprint") from exc

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(filename=str(html_path), base_url=str(html_path.parent)).write_pdf(str(pdf_path))
    return pdf_path
