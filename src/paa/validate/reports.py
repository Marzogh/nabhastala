from __future__ import annotations

from pathlib import Path


def generate_validation_report(year: int, site_id: str, output_dir: Path) -> Path:
    data_dir = output_dir / str(year) / "data"
    report = output_dir / str(year) / "logs" / "validation_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)

    expected = [
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
        "meteor_showers.csv",
    ]

    lines = [f"# Validation report", "", f"- year: {year}", f"- site: {site_id}", ""]
    for name in expected:
        p = data_dir / name
        if not p.exists():
            lines.append(f"- [FAIL] missing `{name}`")
            continue
        content = p.read_text(encoding="utf-8").strip().splitlines()
        rows = max(0, len(content) - 1)
        status = "PASS" if rows > 0 else "WARN"
        lines.append(f"- [{status}] `{name}` rows={rows}")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
