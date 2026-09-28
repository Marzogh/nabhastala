from __future__ import annotations

import csv
from pathlib import Path

from paa.validate.reports import generate_validation_report, validation_failures


def _write_comets(path: Path, statuses: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("target", "calc_status"))
        writer.writeheader()
        for index, status in enumerate(statuses):
            writer.writerow({"target": f"C/{index}", "calc_status": status})


def _touch_other_datasets(data_dir: Path) -> None:
    from paa.validate.reports import EXPECTED_DATASETS

    for name in EXPECTED_DATASETS:
        if name == "comets.csv":
            continue
        (data_dir / name).write_text("value\n1\n", encoding="utf-8")


def test_validation_rejects_widespread_comet_query_failure(tmp_path: Path) -> None:
    data_dir = tmp_path / "output" / "se_qld" / "2026" / "data"
    data_dir.mkdir(parents=True)
    _touch_other_datasets(data_dir)
    _write_comets(data_dir / "comets.csv", ["query_failed", "query_failed", "visible"])

    failures = validation_failures(2026, "se_qld", tmp_path / "output")
    report = generate_validation_report(2026, "se_qld", tmp_path / "output")

    assert "comets.csv query_failed=2/3" in failures
    assert "[FAIL] `comets.csv` rows=3 query_failed=2/3" in report.read_text(encoding="utf-8")


def test_validation_accepts_isolated_comet_query_failure(tmp_path: Path) -> None:
    data_dir = tmp_path / "output" / "se_qld" / "2026" / "data"
    data_dir.mkdir(parents=True)
    _touch_other_datasets(data_dir)
    _write_comets(data_dir / "comets.csv", ["visible", "not_visible", "query_failed"])

    failures = validation_failures(2026, "se_qld", tmp_path / "output")

    assert not any(failure.startswith("comets.csv query_failed") for failure in failures)


def test_validation_rejects_empty_occultation_dataset(tmp_path: Path) -> None:
    data_dir = tmp_path / "output" / "se_qld" / "2026" / "data"
    data_dir.mkdir(parents=True)
    _touch_other_datasets(data_dir)
    _write_comets(data_dir / "comets.csv", ["visible"])
    (data_dir / "lunar_occultations.csv").write_text(
        "datetime_local,target\n", encoding="utf-8"
    )

    failures = validation_failures(2026, "se_qld", tmp_path / "output")

    assert "lunar_occultations.csv empty" in failures
