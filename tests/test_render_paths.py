import csv
import json
from pathlib import Path

from paa.render.html import render_annual_html
from paa.validate.reports import generate_validation_report

FIXTURE = Path(__file__).parent / "fixtures" / "stage1_almanac.json"


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


def _write_legacy_manifest(year_dir: Path, site_id: str = "se_qld") -> None:
    manifest = year_dir / "logs" / "run_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"site_id": site_id}), encoding="utf-8")


def test_renderer_reads_legacy_data_but_only_writes_canonical_tree(tmp_path: Path) -> None:
    output = tmp_path / "output"
    legacy = output / "2027"
    _write_fixture(legacy / "data")
    _write_legacy_manifest(legacy)
    chart = legacy / "charts" / "milky_way_windows.png"
    chart.parent.mkdir(parents=True)
    chart.write_bytes(b"fixture-chart")

    rendered = render_annual_html(2027, "se_qld", output)

    assert rendered == output / "se_qld" / "2027" / "almanac.html"
    assert not (legacy / "almanac.html").exists()
    assert (rendered.parent / "months" / "01.html").exists()
    assert (rendered.parent / "charts" / "milky_way_windows.png").read_bytes() == b"fixture-chart"
    assert (rendered.parent / "data" / "moon_phase.csv").exists()
    assert (rendered.parent / "data" / "index.html").exists()
    assert (output / "index.html").exists()
    html = rendered.read_text(encoding="utf-8")
    assert "Year at a glance" in html
    assert "Monthly field guides" in html
    assert "Browse data and downloads" in html
    assert "<table" not in html
    assert "<script>unsafe</script>" not in html
    assert "&lt;script&gt;unsafe&lt;/script&gt;" not in html
    assert "<script>unsafe</script>" in (
        rendered.parent / "data" / "comets.csv"
    ).read_text(encoding="utf-8")


def test_validation_reads_legacy_data_and_writes_canonical_report(tmp_path: Path) -> None:
    output = tmp_path / "output"
    legacy = output / "2027"
    _write_fixture(legacy / "data")
    _write_legacy_manifest(legacy)

    report = generate_validation_report(2027, "se_qld", output)

    assert report == output / "se_qld" / "2027" / "logs" / "validation_report.md"
    assert report.exists()
    assert not (output / "2027" / "logs" / "validation_report.md").exists()
