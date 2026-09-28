from __future__ import annotations

import csv
import json
from pathlib import Path

import paa.render.pdf as pdf_module

FIXTURE = Path(__file__).parent / "fixtures" / "stage1_almanac.json"


def _write_fixture(data_dir: Path) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename, table in fixture.items():
        with (data_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(table["headers"])
            writer.writerows(table["rows"])


def test_field_pdf_uses_dedicated_curated_print_composition(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "output"
    _write_fixture(output / "se_qld" / "2027" / "data")
    monkeypatch.chdir(tmp_path)

    def fake_render(html_path: Path, pdf_path: Path) -> Path:
        assert html_path.parent == Path("tmp/pdfs")
        html = html_path.read_text(encoding="utf-8")
        assert "2027 observing almanac" in html
        assert "Annual summary" in html
        assert "Galactic Centre observing time" in html
        assert html.count('class="page month-page"') == 12
        assert "Using this field edition" in html
        assert "Jupiter moon offsets" not in html
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-fixture")
        return pdf_path

    monkeypatch.setattr(pdf_module, "render_pdf_from_html", fake_render)
    rendered = pdf_module.render_field_pdf(2027, "se_qld", output)

    assert rendered == output / "pdf" / "nabhastala-2027-se-qld-field-edition.pdf"
    assert rendered.read_bytes() == b"%PDF-fixture"


def test_pdf_template_and_styles_are_packaged() -> None:
    render_dir = Path(pdf_module.__file__).parent
    assert (render_dir / "templates" / "field_pdf.html").is_file()
    assert (render_dir / "static" / "field_pdf.css").is_file()
