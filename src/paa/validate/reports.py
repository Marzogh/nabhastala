from __future__ import annotations

import csv
from pathlib import Path

from paa.paths import resolve_site_year_dir, site_year_dir


def validation_failures(year: int, site_id: str, output_dir: Path) -> list[str]:
    source_dir = resolve_site_year_dir(output_dir, site_id, year, required="data")
    data_dir = source_dir / "data"
    failures = [name for name in EXPECTED_DATASETS if not (data_dir / name).exists()]
    comet_path = data_dir / "comets.csv"
    if comet_path.exists():
        failed, total = _comet_query_failures(comet_path)
        if total and failed / total > 0.5:
            failures.append(f"comets.csv query_failed={failed}/{total}")
    occultation_path = data_dir / "lunar_occultations.csv"
    if occultation_path.exists() and not _csv_has_rows(occultation_path):
        failures.append("lunar_occultations.csv empty")
    phenomena_path = data_dir / "astronomical_phenomena.csv"
    if phenomena_path.exists() and not _csv_has_rows(phenomena_path):
        failures.append("astronomical_phenomena.csv empty")
    return failures


EXPECTED_DATASETS = (
    "sun_twilight.csv",
    "moon_phase.csv",
    "moonrise_moonset.csv",
    "moon_dark_windows.csv",
    "milky_way_windows.csv",
    "planet_visibility_daily.csv",
    "jupiter_moons.csv",
    "saturn_moons.csv",
    "minor_planets.csv",
    "comets.csv",
    "lunar_occultations.csv",
    "astronomical_phenomena.csv",
    "meteor_showers.csv",
)


def _comet_query_failures(path: Path) -> tuple[int, int]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sum(row.get("calc_status") == "query_failed" for row in rows), len(rows)


def _csv_has_rows(path: Path) -> bool:
    with path.open(encoding="utf-8", newline="") as handle:
        return next(csv.DictReader(handle), None) is not None


def generate_validation_report(year: int, site_id: str, output_dir: Path) -> Path:
    source_dir = resolve_site_year_dir(output_dir, site_id, year, required="data")
    data_dir = source_dir / "data"
    report = site_year_dir(output_dir, site_id, year) / "logs" / "validation_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Validation report", "", f"- year: {year}", f"- site: {site_id}", ""]
    for name in EXPECTED_DATASETS:
        p = data_dir / name
        if not p.exists():
            lines.append(f"- [FAIL] missing `{name}`")
            continue
        content = p.read_text(encoding="utf-8").strip().splitlines()
        rows = max(0, len(content) - 1)
        if name == "comets.csv" and rows:
            failed, total = _comet_query_failures(p)
            if failed / total > 0.5:
                lines.append(
                    f"- [FAIL] `{name}` rows={rows} query_failed={failed}/{total}"
                )
                continue
            lines.append(
                f"- [PASS] `{name}` rows={rows} query_failed={failed}/{total}"
            )
            continue
        required_nonempty = {"lunar_occultations.csv", "astronomical_phenomena.csv"}
        status = "PASS" if rows > 0 else "FAIL" if name in required_nonempty else "WARN"
        lines.append(f"- [{status}] `{name}` rows={rows}")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
