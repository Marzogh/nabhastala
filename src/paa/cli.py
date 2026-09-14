from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from paa.compute.meteors import compute_meteor_showers
from paa.compute.milky_way import compute_milky_way_outputs, save_milky_way_chart
from paa.compute.minor_planets import compute_minor_planets_and_comets
from paa.compute.moons import compute_moon_offsets, save_moon_strip_chart
from paa.compute.planets import compute_planet_visibility
from paa.compute.conjunctions import compute_conjunctions
from paa.compute.sun_moon import build_dark_windows, generate_sun_moon_tables
from paa.compute.ui_notes import generate_ui_notes
from paa.config import get_site, load_sites
from paa.io.postgres import ensure_schema, replace_rows, resolve_database_url, upsert_run
from paa.io.provenance import write_run_manifest
from paa.logging_config import configure_logging
from paa.render.html import render_annual_html
from paa.render.pdf import render_pdf_from_html
from paa.sources.occult_import import import_latest_occult_cache
from paa.validate.reports import generate_validation_report


DEFAULT_SITES = {
    "sites": [
        {
            "id": "se_qld",
            "name": "South East Queensland, Australia",
            "latitude_deg": -27.5,
            "longitude_deg": 153.0,
            "elevation_m": 50,
            "timezone": "Australia/Brisbane",
            "bortle": None,
        },
        {
            "id": "southern_tasmania",
            "name": "Southern Tasmania, Australia",
            "latitude_deg": -42.75,
            "longitude_deg": 146.98,
            "elevation_m": 120,
            "timezone": "Australia/Hobart",
            "bortle": None,
        },
        {
            "id": "malabar_coast",
            "name": "Malabar Coast, India",
            "latitude_deg": 11.2588,
            "longitude_deg": 75.7804,
            "elevation_m": 5,
            "timezone": "Asia/Kolkata",
            "bortle": None,
        },
    ]
}

DEFAULT_ALMANAC = {
    "year": 2027,
    "darkness": {"twilight": "astronomical", "sun_altitude_deg": -18, "min_dark_window_minutes": 60},
    "moon": {"max_illumination_for_dark_imaging": 0.25, "require_moon_below_horizon": True},
    "milky_way": {"useful_altitude_deg": 20, "excellent_altitude_deg": 25, "scan_step_minutes": 10},
    "planets": {"min_altitude_deg": 25, "excellent_altitude_deg": 45},
}

SECTION_ORDER = [
    "sun_moon",
    "milky_way",
    "planets",
    "moons",
    "minor_planets",
    "comets",
    "occultations",
    "meteors",
    "conjunctions",
    "ui_notes_context",
    "ui_notes_tonight",
    "ui_notes_milky_way",
    "ui_notes_events",
    "ui_notes_validation",
    "ui_notes_recommendations",
    "ui_notes_bundle",
]

SECTION_DEPS = {
    "sun_moon": set(),
    "milky_way": {"sun_moon"},
    "planets": set(),
    "moons": {"planets"},
    "minor_planets": set(),
    "comets": set(),
    "occultations": set(),
    "meteors": set(),
    "conjunctions": set(),
    "ui_notes_context": {"sun_moon"},
    "ui_notes_tonight": {"sun_moon"},
    "ui_notes_milky_way": {"milky_way"},
    "ui_notes_events": {"sun_moon", "milky_way", "planets", "minor_planets", "comets", "occultations", "meteors", "conjunctions"},
    "ui_notes_validation": {"sun_moon", "milky_way", "planets", "moons", "occultations"},
    "ui_notes_recommendations": {"sun_moon", "occultations"},
    "ui_notes_bundle": {
        "ui_notes_context",
        "ui_notes_tonight",
        "ui_notes_milky_way",
        "ui_notes_events",
        "ui_notes_validation",
        "ui_notes_recommendations",
    },
}

SECTION_ALIASES = {
    "ui_notes_all": {
        "ui_notes_context",
        "ui_notes_tonight",
        "ui_notes_milky_way",
        "ui_notes_events",
        "ui_notes_validation",
        "ui_notes_recommendations",
        "ui_notes_bundle",
    }
}


def cmd_init_config(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "sites.yaml": DEFAULT_SITES,
        "almanac.yaml": DEFAULT_ALMANAC,
        "horizons_objects.yaml": {"major_planets": {}},
        "meteor_showers.yaml": {"showers": []},
        "target_catalog.yaml": {"targets": []},
    }
    for name, content in files.items():
        path = output / name
        if not path.exists():
            path.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    print(f"Initialized config in {output}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    sites = load_sites(Path(args.config_dir) / "sites.yaml")
    selected = get_site(sites, args.site)
    out = Path("output") / str(args.year) / "cache" / "_run"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fetch_stub.txt").write_text(f"fetch prepared for {selected.id}\n", encoding="utf-8")
    print(f"Fetch complete for {selected.id} ({args.year})")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    config_dir = Path(args.config_dir)
    sites = load_sites(config_dir / "sites.yaml")
    site = get_site(sites, args.site)
    almanac = yaml.safe_load((config_dir / "almanac.yaml").read_text(encoding="utf-8")) or {}

    darkness = almanac.get("darkness", {})
    min_dark_minutes = int(darkness.get("min_dark_window_minutes", 60))
    max_illum = float(almanac.get("moon", {}).get("max_illumination_for_dark_imaging", 0.25))

    out = Path("output") / str(args.year) / "data"
    out.mkdir(parents=True, exist_ok=True)
    explicit_requested = _parse_explicit_sections(args.sections)
    requested = _resolve_requested_sections(args.sections)
    manifest_path = Path("output") / str(args.year) / "logs" / "section_manifest.json"
    section_manifest = _read_json(manifest_path) if manifest_path.exists() else {}
    ctx: dict[str, list[dict]] = {}

    def load_csv(name: str) -> list[dict]:
        if name in ctx:
            return ctx[name]
        p = out / f"{name}.csv"
        rows = _read_csv(p) if p.exists() else []
        ctx[name] = rows
        return rows

    for section in SECTION_ORDER:
        if section not in requested:
            continue
        fp = _section_fingerprint(section, args.year, args.site, config_dir, out)
        prev = section_manifest.get(section, {})
        force_this = args.force and section in explicit_requested
        if (not force_this) and prev.get("fingerprint") == fp and _section_outputs_exist(section, out):
            print(f"[build] {section}: unchanged; skip", flush=True)
            continue

        if section == "sun_moon":
            print("[build] sun/moon tables...", flush=True)
            twilight_rows, moon_phase_rows, moonrise_rows = generate_sun_moon_tables(args.year, site)
            dark_rows = build_dark_windows(twilight_rows, moon_phase_rows, moonrise_rows, min_dark_minutes=min_dark_minutes, max_illum=max_illum)
            _write_csv(out / "sun_twilight.csv", twilight_rows)
            _write_csv(out / "moon_phase.csv", moon_phase_rows)
            _write_csv(out / "moonrise_moonset.csv", moonrise_rows)
            _write_csv(out / "moon_dark_windows.csv", dark_rows)
            ctx["sun_twilight"], ctx["moon_phase"], ctx["moonrise_moonset"], ctx["moon_dark_windows"] = twilight_rows, moon_phase_rows, moonrise_rows, dark_rows
        elif section == "milky_way":
            print("[build] milky way windows...", flush=True)
            milky_cfg = almanac.get("milky_way", {})
            mw_rows, mw_monthly_rows, mw_points = compute_milky_way_outputs(
                dark_windows_csv=out / "moon_dark_windows.csv",
                latitude_deg=site.latitude_deg,
                longitude_deg=site.longitude_deg,
                elevation_m=site.elevation_m,
                useful_alt_deg=float(milky_cfg.get("useful_altitude_deg", 20)),
                excellent_alt_deg=float(milky_cfg.get("excellent_altitude_deg", 25)),
                step_minutes=int(milky_cfg.get("scan_step_minutes", 10)),
            )
            _write_csv(out / "milky_way_windows.csv", mw_rows)
            _write_csv(out / "milky_way_monthly_summary.csv", mw_monthly_rows)
            save_milky_way_chart(mw_points, Path("output") / str(args.year) / "charts" / "milky_way_windows.png")
            ctx["milky_way_windows"], ctx["milky_way_monthly_summary"] = mw_rows, mw_monthly_rows
        elif section == "planets":
            print("[build] planet visibility...", flush=True)
            planets_cfg = almanac.get("planets", {})
            planet_daily, planet_monthly = compute_planet_visibility(
                year=args.year,
                latitude_deg=site.latitude_deg,
                longitude_deg=site.longitude_deg,
                elevation_m=site.elevation_m,
                timezone=site.timezone,
                min_alt_deg=float(planets_cfg.get("min_altitude_deg", 25)),
                excellent_alt_deg=float(planets_cfg.get("excellent_altitude_deg", 45)),
            )
            _write_csv(out / "planet_visibility_daily.csv", planet_daily)
            _write_csv(out / "planet_visibility_monthly_summary.csv", planet_monthly)
            ctx["planet_visibility_daily"], ctx["planet_visibility_monthly_summary"] = planet_daily, planet_monthly
        elif section == "moons":
            print("[build] moon offsets...", flush=True)
            jupiter_moons, saturn_moons = compute_moon_offsets(
                year=args.year,
                site_lat=site.latitude_deg,
                site_lon=site.longitude_deg,
                site_elev=site.elevation_m,
                site_tz=site.timezone,
                config_dir=config_dir,
                planet_daily_csv=out / "planet_visibility_daily.csv",
            )
            _write_csv(out / "jupiter_moons.csv", jupiter_moons)
            _write_csv(out / "saturn_moons.csv", saturn_moons)
            save_moon_strip_chart(jupiter_moons, Path("output") / str(args.year) / "charts" / "jupiter_moons" / "strip_chart.png", "Jupiter Moon Relative Offsets")
            save_moon_strip_chart(saturn_moons, Path("output") / str(args.year) / "charts" / "saturn_moons" / "strip_chart.png", "Saturn Moon Relative Offsets")
            ctx["jupiter_moons"], ctx["saturn_moons"] = jupiter_moons, saturn_moons
        elif section in {"minor_planets", "comets"}:
            print(f"[build] {section.replace('_', ' ')}...", flush=True)
            minor_rows = ctx.get("minor_planets")
            comet_rows = ctx.get("comets")
            if minor_rows is None or comet_rows is None:
                minor_rows, comet_rows = compute_minor_planets_and_comets(
                    year=args.year,
                    site_lat=site.latitude_deg,
                    site_lon=site.longitude_deg,
                    site_elev=site.elevation_m,
                    timezone_name=site.timezone,
                    config_dir=config_dir,
                )
            if section == "minor_planets":
                _write_csv(out / "minor_planets.csv", minor_rows)
            else:
                _write_csv(out / "comets.csv", comet_rows)
            ctx["minor_planets"], ctx["comets"] = minor_rows, comet_rows
        elif section == "occultations":
            print("[build] occult import...", flush=True)
            occult_rows = import_latest_occult_cache(args.year, args.site, site.timezone, almanac.get("occultations", {}))
            _write_csv(out / "lunar_occultations.csv", occult_rows)
            ctx["lunar_occultations"] = occult_rows
        elif section == "meteors":
            print("[build] meteor showers...", flush=True)
            meteor_rows = compute_meteor_showers(args.year, site.latitude_deg, site.longitude_deg, site.elevation_m, site.timezone, config_dir)
            _write_csv(out / "meteor_showers.csv", meteor_rows)
            ctx["meteor_showers"] = meteor_rows
        elif section == "conjunctions":
            print("[build] conjunctions...", flush=True)
            conjunction_rows = compute_conjunctions(
                year=args.year,
                latitude_deg=site.latitude_deg,
                longitude_deg=site.longitude_deg,
                elevation_m=site.elevation_m,
                timezone=site.timezone,
            )
            _write_csv(out / "conjunctions.csv", conjunction_rows)
            ctx["conjunctions"] = conjunction_rows
        elif section.startswith("ui_notes_"):
            all_notes = _build_all_ui_notes(
                ctx=ctx,
                load_csv=load_csv,
                year=args.year,
                site_name=site.name,
                timezone=site.timezone,
            )
            if section == "ui_notes_context":
                print("[build] ui notes context...", flush=True)
                notes = [n for n in all_notes if n.get("section") == "hero"]
                _write_csv(out / "ui_notes.context.csv", notes)
                ctx["ui_notes_context"] = notes
            elif section == "ui_notes_tonight":
                print("[build] ui notes tonight...", flush=True)
                notes = [n for n in all_notes if n.get("section") in {"tonight", "moon"}]
                _write_csv(out / "ui_notes.tonight.csv", notes)
                ctx["ui_notes_tonight"] = notes
            elif section == "ui_notes_milky_way":
                print("[build] ui notes milky way...", flush=True)
                notes = [n for n in all_notes if n.get("section") == "milky_way"]
                _write_csv(out / "ui_notes.milky_way.csv", notes)
                ctx["ui_notes_milky_way"] = notes
            elif section == "ui_notes_events":
                print("[build] ui notes events...", flush=True)
                notes = [n for n in all_notes if n.get("section") == "events"]
                _write_csv(out / "ui_notes.events.csv", notes)
                ctx["ui_notes_events"] = notes
            elif section == "ui_notes_validation":
                print("[build] ui notes validation...", flush=True)
                notes = [n for n in all_notes if n.get("section") == "validation"]
                _write_csv(out / "ui_notes.validation.csv", notes)
                ctx["ui_notes_validation"] = notes
            elif section == "ui_notes_recommendations":
                print("[build] ui notes recommendations...", flush=True)
                notes = [n for n in all_notes if n.get("section") == "recommendations"]
                _write_csv(out / "ui_notes.recommendations.csv", notes)
                ctx["ui_notes_recommendations"] = notes
            elif section == "ui_notes_bundle":
                print("[build] ui notes bundle...", flush=True)
                notes = _collect_ui_notes_bundle(out)
                _write_csv(out / "ui_notes.csv", notes)
                (out / "ui_notes.json").write_text(json.dumps(notes, indent=2), encoding="utf-8")
                ctx["ui_notes"] = notes

        section_manifest[section] = {"fingerprint": fp}
        _write_json(manifest_path, section_manifest)

    twilight_rows = load_csv("sun_twilight")
    moon_phase_rows = load_csv("moon_phase")
    moonrise_rows = load_csv("moonrise_moonset")
    dark_rows = load_csv("moon_dark_windows")
    mw_rows = load_csv("milky_way_windows")
    mw_monthly_rows = load_csv("milky_way_monthly_summary")
    planet_daily = load_csv("planet_visibility_daily")
    planet_monthly = load_csv("planet_visibility_monthly_summary")
    jupiter_moons = load_csv("jupiter_moons")
    saturn_moons = load_csv("saturn_moons")
    minor_rows = load_csv("minor_planets")
    comet_rows = load_csv("comets")
    occult_rows = load_csv("lunar_occultations")
    meteor_rows = load_csv("meteor_showers")
    conjunction_rows = load_csv("conjunctions")
    ui_notes = load_csv("ui_notes")

    run_id = None
    if not args.skip_db:
        database_url = resolve_database_url(args.database_url)
        ensure_schema(database_url)
        run_id = upsert_run(database_url, args.year, args.site)
        replace_rows(database_url, "sun_twilight", run_id, twilight_rows)
        replace_rows(database_url, "moon_phase", run_id, moon_phase_rows)
        replace_rows(database_url, "moonrise_moonset", run_id, moonrise_rows)
        replace_rows(database_url, "moon_dark_windows", run_id, dark_rows)
        replace_rows(database_url, "milky_way_windows", run_id, mw_rows)
        replace_rows(database_url, "milky_way_monthly_summary", run_id, mw_monthly_rows)
        replace_rows(database_url, "planet_visibility_daily", run_id, planet_daily)
        replace_rows(database_url, "planet_visibility_monthly", run_id, planet_monthly)
        replace_rows(database_url, "jupiter_moon_offsets", run_id, jupiter_moons)
        replace_rows(database_url, "saturn_moon_offsets", run_id, saturn_moons)
        replace_rows(database_url, "minor_planet_opportunities", run_id, minor_rows)
        replace_rows(database_url, "comet_opportunities", run_id, comet_rows)
        replace_rows(database_url, "lunar_occultations", run_id, occult_rows)
        replace_rows(database_url, "meteor_showers", run_id, meteor_rows)
        replace_rows(database_url, "conjunctions", run_id, conjunction_rows)
        replace_rows(database_url, "ui_notes", run_id, ui_notes)

    report = generate_validation_report(args.year, args.site, Path("output"))
    manifest = write_run_manifest(args.year, args.site, config_dir=config_dir, output_dir=Path("output"), run_id=run_id)

    print(f"Build complete for {args.site} ({args.year}) through Milestone 7; run_id={run_id}")
    print(f"Validation: {report}")
    print(f"Manifest: {manifest}")
    return 0


def cmd_import_occult(args: argparse.Namespace) -> int:
    source = Path(args.file)
    if not source.exists():
        raise SystemExit(f"File not found: {source}")
    cache_dir = Path("output") / str(args.year) / "cache" / "occult" / args.site
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / source.name
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Imported Occult file to {target}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    html_path = render_annual_html(args.year, args.site, Path("output"))
    if args.format == "html":
        print(f"Rendered HTML: {html_path}")
        return 0
    if args.format == "pdf":
        pdf_path = Path("output") / str(args.year) / "almanac.pdf"
        render_pdf_from_html(html_path, pdf_path)
        print(f"Rendered PDF: {pdf_path}")
        return 0
    raise SystemExit("format must be one of: html, pdf")


def cmd_validate(args: argparse.Namespace) -> int:
    log_path = Path("output") / str(args.year) / "logs" / "run.log"
    configure_logging(log_path)
    report = generate_validation_report(args.year, args.site, Path("output"))
    print(f"Validation complete: {report}")
    return 0


def cmd_db_init(args: argparse.Namespace) -> int:
    db = resolve_database_url(args.database_url)
    ensure_schema(db)
    print("Database schema ready")
    return 0


def cmd_db_check(args: argparse.Namespace) -> int:
    db = resolve_database_url(args.database_url)
    import psycopg

    with psycopg.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM paa.runs")
            runs = cur.fetchone()[0]
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='paa' ORDER BY table_name")
            tables = [r[0] for r in cur.fetchall()]
    print(f"runs={runs}")
    print("tables=" + ",".join(tables))
    return 0


def cmd_view(args: argparse.Namespace) -> int:
    year = args.year
    if year is None:
        raise SystemExit("Provide a year via --year YYYY or shorthand like --2027")
    report = Path("output") / str(year) / "almanac.html"
    if not report.exists():
        raise SystemExit(f"Report not found: {report}. Run build/render first.")
    subprocess.run(["open", str(report)], check=True)
    print(f"Opened {report}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astro-almanac", description="Personal Astronomy Almanac CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-config")
    p.add_argument("--output", default="config")
    p.set_defaults(func=cmd_init_config)

    p = sub.add_parser("fetch")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--site", required=True)
    p.add_argument("--config-dir", default="config")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("build")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--site", required=True)
    p.add_argument("--config-dir", default="config")
    p.add_argument("--database-url", default=None)
    p.add_argument("--skip-db", action="store_true")
    p.add_argument("--sections", default="all", help="Comma list: sun_moon,milky_way,planets,moons,minor_planets,comets,occultations,meteors,conjunctions,ui_notes_context,ui_notes_tonight,ui_notes_milky_way,ui_notes_events,ui_notes_validation,ui_notes_recommendations,ui_notes_bundle,ui_notes_all or 'all'")
    p.add_argument("--force", action="store_true", help="Rebuild selected sections even when fingerprint is unchanged")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("import-occult")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--site", required=True)
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_import_occult)

    p = sub.add_parser("render")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--site", required=True)
    p.add_argument("--format", default="html")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("validate")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--site", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("db-init")
    p.add_argument("--database-url", default=None)
    p.set_defaults(func=cmd_db_init)

    p = sub.add_parser("db-check")
    p.add_argument("--database-url", default=None)
    p.set_defaults(func=cmd_db_check)

    p = sub.add_parser("view")
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--2027", dest="year", action="store_const", const=2027)
    p.set_defaults(func=cmd_view)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _build_all_ui_notes(*, ctx: dict[str, list[dict]], load_csv, year: int, site_name: str, timezone: str) -> list[dict]:
    cached = ctx.get("_ui_notes_all")
    if cached is not None:
        return cached

    twilight_rows = load_csv("sun_twilight")
    moon_phase_rows = load_csv("moon_phase")
    moonrise_rows = load_csv("moonrise_moonset")
    dark_rows = load_csv("moon_dark_windows")
    mw_rows = load_csv("milky_way_windows")
    mw_monthly_rows = load_csv("milky_way_monthly_summary")
    planet_daily = load_csv("planet_visibility_daily")
    planet_monthly = load_csv("planet_visibility_monthly_summary")
    minor_rows = load_csv("minor_planets")
    comet_rows = load_csv("comets")
    occult_rows = load_csv("lunar_occultations")
    meteor_rows = load_csv("meteor_showers")
    conjunction_rows = load_csv("conjunctions")
    jupiter_moons = load_csv("jupiter_moons")
    saturn_moons = load_csv("saturn_moons")

    validation_items = [
        ("sun_twilight", bool(twilight_rows)),
        ("moon_phase", bool(moon_phase_rows)),
        ("moonrise_moonset", bool(moonrise_rows)),
        ("moon_dark_windows", bool(dark_rows)),
        ("milky_way_windows", bool(mw_rows)),
        ("planet_visibility_daily", bool(planet_daily)),
        ("jupiter_moons", bool(jupiter_moons)),
        ("saturn_moons", bool(saturn_moons)),
        ("lunar_occultations", bool(occult_rows)),
    ]

    notes = generate_ui_notes(
        year=year,
        site_name=site_name,
        timezone=timezone,
        dark_rows=dark_rows,
        moon_phase_rows=moon_phase_rows,
        moonrise_rows=moonrise_rows,
        twilight_rows=twilight_rows,
        milky_monthly_rows=mw_monthly_rows,
        milky_rows=mw_rows,
        planet_daily_rows=planet_daily,
        planet_monthly_rows=planet_monthly,
        minor_rows=minor_rows,
        comet_rows=comet_rows,
        occult_rows=occult_rows,
        meteor_rows=meteor_rows,
        conjunction_rows=conjunction_rows,
        validation_items=validation_items,
    )
    ctx["_ui_notes_all"] = notes
    return notes


def _collect_ui_notes_bundle(out: Path) -> list[dict]:
    files = [
        "ui_notes.context.csv",
        "ui_notes.tonight.csv",
        "ui_notes.milky_way.csv",
        "ui_notes.events.csv",
        "ui_notes.validation.csv",
        "ui_notes.recommendations.csv",
    ]
    rows: list[dict] = []
    for name in files:
        p = out / name
        if p.exists():
            rows.extend(_read_csv(p))
    return rows


def _resolve_requested_sections(raw: str) -> set[str]:
    s = (raw or "all").strip().lower()
    if s == "all":
        return set(SECTION_ORDER)
    requested = {x.strip() for x in s.split(",") if x.strip()}
    expanded_aliases: set[str] = set()
    for item in requested:
        if item in SECTION_ALIASES:
            expanded_aliases.update(SECTION_ALIASES[item])
        else:
            expanded_aliases.add(item)
    requested = expanded_aliases
    unknown = requested.difference(set(SECTION_ORDER))
    if unknown:
        raise SystemExit(f"Unknown sections: {','.join(sorted(unknown))}")
    expanded = set()
    stack = list(requested)
    while stack:
        cur = stack.pop()
        if cur in expanded:
            continue
        expanded.add(cur)
        stack.extend(SECTION_DEPS.get(cur, set()))
    return expanded


def _parse_explicit_sections(raw: str) -> set[str]:
    s = (raw or "all").strip().lower()
    if s == "all":
        return set(SECTION_ORDER)
    requested = {x.strip() for x in s.split(",") if x.strip()}
    expanded_aliases: set[str] = set()
    for item in requested:
        if item in SECTION_ALIASES:
            expanded_aliases.update(SECTION_ALIASES[item])
        else:
            expanded_aliases.add(item)
    unknown = expanded_aliases.difference(set(SECTION_ORDER))
    if unknown:
        raise SystemExit(f"Unknown sections: {','.join(sorted(unknown))}")
    return expanded_aliases


def _section_outputs_exist(section: str, out: Path) -> bool:
    req = {
        "sun_moon": ["sun_twilight.csv", "moon_phase.csv", "moonrise_moonset.csv", "moon_dark_windows.csv"],
        "milky_way": ["milky_way_windows.csv", "milky_way_monthly_summary.csv"],
        "planets": ["planet_visibility_daily.csv", "planet_visibility_monthly_summary.csv"],
        "moons": ["jupiter_moons.csv", "saturn_moons.csv"],
        "minor_planets": ["minor_planets.csv"],
        "comets": ["comets.csv"],
        "occultations": ["lunar_occultations.csv"],
        "meteors": ["meteor_showers.csv"],
        "conjunctions": ["conjunctions.csv"],
        "ui_notes_context": ["ui_notes.context.csv"],
        "ui_notes_tonight": ["ui_notes.tonight.csv"],
        "ui_notes_milky_way": ["ui_notes.milky_way.csv"],
        "ui_notes_events": ["ui_notes.events.csv"],
        "ui_notes_validation": ["ui_notes.validation.csv"],
        "ui_notes_recommendations": ["ui_notes.recommendations.csv"],
        "ui_notes_bundle": ["ui_notes.csv", "ui_notes.json"],
    }[section]
    return all((out / f).exists() for f in req)


def _section_fingerprint(section: str, year: int, site: str, config_dir: Path, out: Path) -> str:
    h = hashlib.sha256()
    h.update(f"section={section}|year={year}|site={site}".encode("utf-8"))
    for p in [config_dir / "sites.yaml", config_dir / "almanac.yaml"]:
        if p.exists():
            h.update(p.read_bytes())
    upstream = {
        "milky_way": ["moon_dark_windows.csv"],
        "moons": ["planet_visibility_daily.csv"],
        "ui_notes_context": [
            "sun_twilight.csv",
            "moon_phase.csv",
            "moonrise_moonset.csv",
            "moon_dark_windows.csv",
        ],
        "ui_notes_tonight": [
            "sun_twilight.csv",
            "moon_phase.csv",
            "moonrise_moonset.csv",
            "moon_dark_windows.csv",
        ],
        "ui_notes_milky_way": [
            "milky_way_windows.csv",
            "milky_way_monthly_summary.csv",
        ],
        "ui_notes_events": [
            "sun_twilight.csv",
            "moon_phase.csv",
            "moonrise_moonset.csv",
            "moon_dark_windows.csv",
            "milky_way_windows.csv",
            "milky_way_monthly_summary.csv",
            "planet_visibility_daily.csv",
            "planet_visibility_monthly_summary.csv",
            "minor_planets.csv",
            "comets.csv",
            "lunar_occultations.csv",
            "meteor_showers.csv",
            "conjunctions.csv",
        ],
        "ui_notes_validation": [
            "sun_twilight.csv",
            "moon_phase.csv",
            "moonrise_moonset.csv",
            "moon_dark_windows.csv",
            "milky_way_windows.csv",
            "planet_visibility_daily.csv",
            "jupiter_moons.csv",
            "saturn_moons.csv",
            "lunar_occultations.csv",
        ],
        "ui_notes_recommendations": [
            "sun_twilight.csv",
            "moon_phase.csv",
            "moonrise_moonset.csv",
            "moon_dark_windows.csv",
            "lunar_occultations.csv",
        ],
        "ui_notes_bundle": [
            "ui_notes.context.csv",
            "ui_notes.tonight.csv",
            "ui_notes.milky_way.csv",
            "ui_notes.events.csv",
            "ui_notes.validation.csv",
            "ui_notes.recommendations.csv",
        ],
    }.get(section, [])
    for f in upstream:
        p = out / f
        if p.exists():
            st = p.stat()
            h.update(f"{f}:{st.st_mtime_ns}:{st.st_size}".encode("utf-8"))
    return h.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
