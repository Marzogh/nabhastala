from __future__ import annotations

import os
from datetime import datetime
from typing import Any


def _imports():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("PostgreSQL support requires psycopg. Install dependencies first.") from exc
    return psycopg


def resolve_database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.getenv("PAA_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env:
        return env
    raise RuntimeError("No PostgreSQL URL set. Use --database-url or PAA_DATABASE_URL.")


def ensure_schema(database_url: str) -> None:
    psycopg = _imports()
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS paa")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS paa.runs (
                  run_id BIGSERIAL PRIMARY KEY,
                  year INTEGER NOT NULL,
                  site_id TEXT NOT NULL,
                  built_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                  UNIQUE (year, site_id)
                )
                """
            )

            table_sql = {
                "sun_twilight": """
                    CREATE TABLE IF NOT EXISTS paa.sun_twilight (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      dusk_astronomical_local TIMESTAMPTZ NOT NULL,
                      dawn_astronomical_local TIMESTAMPTZ NOT NULL
                    )
                """,
                "moon_phase": """
                    CREATE TABLE IF NOT EXISTS paa.moon_phase (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      moon_phase_index DOUBLE PRECISION NOT NULL,
                      moon_illumination_fraction DOUBLE PRECISION NOT NULL
                    )
                """,
                "moonrise_moonset": """
                    CREATE TABLE IF NOT EXISTS paa.moonrise_moonset (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      moonrise_local TIMESTAMPTZ NULL,
                      moonset_local TIMESTAMPTZ NULL
                    )
                """,
                "moon_dark_windows": """
                    CREATE TABLE IF NOT EXISTS paa.moon_dark_windows (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      start_local TIMESTAMPTZ NOT NULL,
                      end_local TIMESTAMPTZ NOT NULL,
                      duration_minutes DOUBLE PRECISION NOT NULL,
                      moon_illumination_fraction DOUBLE PRECISION NOT NULL
                    )
                """,
                "milky_way_windows": """
                    CREATE TABLE IF NOT EXISTS paa.milky_way_windows (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      start_local TIMESTAMPTZ NOT NULL,
                      end_local TIMESTAMPTZ NOT NULL,
                      duration_minutes DOUBLE PRECISION NOT NULL,
                      max_altitude_deg DOUBLE PRECISION NOT NULL,
                      quality TEXT NOT NULL
                    )
                """,
                "milky_way_monthly_summary": """
                    CREATE TABLE IF NOT EXISTS paa.milky_way_monthly_summary (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      month TEXT NOT NULL,
                      window_count INTEGER NOT NULL,
                      excellent_count INTEGER NOT NULL,
                      best_altitude_deg DOUBLE PRECISION NOT NULL
                    )
                """,
                "planet_visibility_daily": """
                    CREATE TABLE IF NOT EXISTS paa.planet_visibility_daily (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      planet TEXT NOT NULL,
                      best_time_local TIMESTAMPTZ NOT NULL,
                      max_altitude_deg DOUBLE PRECISION NOT NULL,
                      solar_elong_deg DOUBLE PRECISION NULL,
                      visibility_rating TEXT NOT NULL
                    )
                """,
                "planet_visibility_monthly": """
                    CREATE TABLE IF NOT EXISTS paa.planet_visibility_monthly (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      month TEXT NOT NULL,
                      planet TEXT NOT NULL,
                      best_date DATE NOT NULL,
                      best_altitude_deg DOUBLE PRECISION NOT NULL,
                      rating TEXT NOT NULL
                    )
                """,
                "jupiter_moon_offsets": """
                    CREATE TABLE IF NOT EXISTS paa.jupiter_moon_offsets (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      datetime_utc TIMESTAMPTZ NOT NULL,
                      datetime_local TIMESTAMPTZ NOT NULL,
                      moon TEXT NOT NULL,
                      dra_arcsec DOUBLE PRECISION NOT NULL,
                      ddec_arcsec DOUBLE PRECISION NOT NULL
                    )
                """,
                "saturn_moon_offsets": """
                    CREATE TABLE IF NOT EXISTS paa.saturn_moon_offsets (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date DATE NOT NULL,
                      datetime_utc TIMESTAMPTZ NOT NULL,
                      datetime_local TIMESTAMPTZ NOT NULL,
                      moon TEXT NOT NULL,
                      dra_arcsec DOUBLE PRECISION NOT NULL,
                      ddec_arcsec DOUBLE PRECISION NOT NULL
                    )
                """,
                "minor_planet_opportunities": """
                    CREATE TABLE IF NOT EXISTS paa.minor_planet_opportunities (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      target TEXT NOT NULL,
                      best_datetime_utc TIMESTAMPTZ NOT NULL,
                      best_datetime_local TIMESTAMPTZ NOT NULL,
                      best_altitude_deg DOUBLE PRECISION NOT NULL,
                      best_apmag DOUBLE PRECISION NOT NULL,
                      solar_elong_deg DOUBLE PRECISION NOT NULL,
                      score INTEGER NOT NULL,
                      rating TEXT NOT NULL
                    )
                """,
                "comet_opportunities": """
                    CREATE TABLE IF NOT EXISTS paa.comet_opportunities (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      target TEXT NOT NULL,
                      best_datetime_utc TIMESTAMPTZ NULL,
                      best_datetime_local TIMESTAMPTZ NULL,
                      best_altitude_deg DOUBLE PRECISION NULL,
                      best_apmag DOUBLE PRECISION NULL,
                      solar_elong_deg DOUBLE PRECISION NULL,
                      score INTEGER NOT NULL,
                      rating TEXT NOT NULL,
                      amateur_chaseable BOOLEAN NOT NULL DEFAULT FALSE,
                      source TEXT NOT NULL DEFAULT 'computed',
                      calc_status TEXT NOT NULL DEFAULT 'unknown',
                      magnitude_note TEXT NULL
                    )
                """,
                "lunar_occultations": """
                    CREATE TABLE IF NOT EXISTS paa.lunar_occultations (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      datetime_local TIMESTAMPTZ NOT NULL,
                      target TEXT NOT NULL,
                      target_mag DOUBLE PRECISION NULL,
                      moon_altitude_deg DOUBLE PRECISION NULL,
                      limb TEXT NULL,
                      event_type TEXT NULL,
                      is_planetary BOOLEAN NOT NULL DEFAULT FALSE,
                      score TEXT NOT NULL
                    )
                """,
                "meteor_showers": """
                    CREATE TABLE IF NOT EXISTS paa.meteor_showers (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      id TEXT NOT NULL,
                      name TEXT NOT NULL,
                      peak_date_local DATE NOT NULL,
                      radiant_alt_peak_deg DOUBLE PRECISION NOT NULL,
                      radiant_alt_predawn_deg DOUBLE PRECISION NOT NULL,
                      moon_illumination_fraction DOUBLE PRECISION NOT NULL,
                      zhr DOUBLE PRECISION NOT NULL,
                      score INTEGER NOT NULL,
                      rating TEXT NOT NULL,
                      notes TEXT NULL
                    )
                """,
                "conjunctions": """
                    CREATE TABLE IF NOT EXISTS paa.conjunctions (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      date_local DATE NOT NULL,
                      event_type TEXT NOT NULL,
                      primary_body TEXT NOT NULL,
                      secondary_body TEXT NOT NULL,
                      separation_deg DOUBLE PRECISION NOT NULL,
                      event_time_local TIMESTAMPTZ NOT NULL,
                      alt_primary_deg DOUBLE PRECISION NOT NULL,
                      alt_secondary_deg DOUBLE PRECISION NOT NULL,
                      sun_altitude_deg DOUBLE PRECISION NOT NULL,
                      solar_elong_deg DOUBLE PRECISION NOT NULL,
                      moon_illumination_fraction DOUBLE PRECISION NOT NULL,
                      visibility_rating TEXT NOT NULL,
                      score INTEGER NOT NULL,
                      is_solar_transit BOOLEAN NOT NULL,
                      safety_note TEXT NULL
                    )
                """,
                "ui_notes": """
                    CREATE TABLE IF NOT EXISTS paa.ui_notes (
                      run_id BIGINT NOT NULL REFERENCES paa.runs(run_id) ON DELETE CASCADE,
                      note_id TEXT NOT NULL,
                      section TEXT NOT NULL,
                      title TEXT NOT NULL,
                      body TEXT NOT NULL,
                      score TEXT NOT NULL,
                      date_local DATE NULL
                    )
                """,
            }
            for sql in table_sql.values():
                cur.execute(sql)

            cur.execute("ALTER TABLE paa.comet_opportunities ALTER COLUMN best_datetime_utc DROP NOT NULL")
            cur.execute("ALTER TABLE paa.comet_opportunities ALTER COLUMN best_datetime_local DROP NOT NULL")
            cur.execute("ALTER TABLE paa.comet_opportunities ALTER COLUMN best_altitude_deg DROP NOT NULL")
            cur.execute("ALTER TABLE paa.comet_opportunities ALTER COLUMN best_apmag DROP NOT NULL")
            cur.execute("ALTER TABLE paa.comet_opportunities ALTER COLUMN solar_elong_deg DROP NOT NULL")
            cur.execute("ALTER TABLE paa.comet_opportunities ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'computed'")
            cur.execute("ALTER TABLE paa.comet_opportunities ADD COLUMN IF NOT EXISTS calc_status TEXT NOT NULL DEFAULT 'unknown'")
            cur.execute("ALTER TABLE paa.comet_opportunities ADD COLUMN IF NOT EXISTS magnitude_note TEXT NULL")
            cur.execute("ALTER TABLE paa.planet_visibility_daily ADD COLUMN IF NOT EXISTS solar_elong_deg DOUBLE PRECISION NULL")


def upsert_run(database_url: str, year: int, site_id: str) -> int:
    psycopg = _imports()
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO paa.runs(year, site_id)
                VALUES (%s, %s)
                ON CONFLICT (year, site_id)
                DO UPDATE SET built_at = now()
                RETURNING run_id
                """,
                (year, site_id),
            )
            run_id = cur.fetchone()[0]
    return int(run_id)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def replace_rows(database_url: str, table: str, run_id: int, rows: list[dict[str, Any]]) -> None:
    psycopg = _imports()
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM paa.{table} WHERE run_id = %s", (run_id,))
            for row in rows:
                if table == "sun_twilight":
                    cur.execute("INSERT INTO paa.sun_twilight VALUES (%s,%s,%s,%s)", (run_id, row["date"], _parse_dt(row["dusk_astronomical_local"]), _parse_dt(row["dawn_astronomical_local"])))
                elif table == "moon_phase":
                    cur.execute("INSERT INTO paa.moon_phase VALUES (%s,%s,%s,%s)", (run_id, row["date"], float(row["moon_phase_index"]), float(row["moon_illumination_fraction"])))
                elif table == "moonrise_moonset":
                    cur.execute("INSERT INTO paa.moonrise_moonset VALUES (%s,%s,%s,%s)", (run_id, row["date"], _parse_dt(row["moonrise_local"]), _parse_dt(row["moonset_local"])))
                elif table == "moon_dark_windows":
                    cur.execute("INSERT INTO paa.moon_dark_windows VALUES (%s,%s,%s,%s,%s,%s)", (run_id, row["date"], _parse_dt(row["start_local"]), _parse_dt(row["end_local"]), float(row["duration_minutes"]), float(row["moon_illumination_fraction"])))
                elif table == "milky_way_windows":
                    cur.execute("INSERT INTO paa.milky_way_windows VALUES (%s,%s,%s,%s,%s,%s,%s)", (run_id, row["date"], _parse_dt(row["start_local"]), _parse_dt(row["end_local"]), float(row["duration_minutes"]), float(row["max_altitude_deg"]), row["quality"]))
                elif table == "milky_way_monthly_summary":
                    cur.execute("INSERT INTO paa.milky_way_monthly_summary VALUES (%s,%s,%s,%s,%s)", (run_id, row["month"], int(row["window_count"]), int(row["excellent_count"]), float(row["best_altitude_deg"])))
                elif table == "planet_visibility_daily":
                    cur.execute(
                        "INSERT INTO paa.planet_visibility_daily (run_id,date,planet,best_time_local,max_altitude_deg,solar_elong_deg,visibility_rating) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (
                            run_id,
                            row["date"],
                            row["planet"],
                            _parse_dt(row["best_time_local"]),
                            float(row["max_altitude_deg"]),
                            _parse_float(row.get("solar_elong_deg")),
                            row["visibility_rating"],
                        ),
                    )
                elif table == "planet_visibility_monthly":
                    cur.execute("INSERT INTO paa.planet_visibility_monthly VALUES (%s,%s,%s,%s,%s,%s)", (run_id, row["month"], row["planet"], row["best_date"], float(row["best_altitude_deg"]), row["rating"]))
                elif table == "jupiter_moon_offsets":
                    cur.execute("INSERT INTO paa.jupiter_moon_offsets VALUES (%s,%s,%s,%s,%s,%s,%s)", (run_id, row["date"], _parse_dt(row["datetime_utc"]), _parse_dt(row["datetime_local"]), row["moon"], float(row["dra_arcsec"]), float(row["ddec_arcsec"])))
                elif table == "saturn_moon_offsets":
                    cur.execute("INSERT INTO paa.saturn_moon_offsets VALUES (%s,%s,%s,%s,%s,%s,%s)", (run_id, row["date"], _parse_dt(row["datetime_utc"]), _parse_dt(row["datetime_local"]), row["moon"], float(row["dra_arcsec"]), float(row["ddec_arcsec"])))
                elif table == "minor_planet_opportunities":
                    cur.execute("INSERT INTO paa.minor_planet_opportunities VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (run_id, row["target"], _parse_dt(row["best_datetime_utc"]), _parse_dt(row["best_datetime_local"]), float(row["best_altitude_deg"]), float(row["best_apmag"]), float(row["solar_elong_deg"]), int(row["score"]), row["rating"]))
                elif table == "comet_opportunities":
                    cur.execute(
                        "INSERT INTO paa.comet_opportunities VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            run_id,
                            row["target"],
                            _parse_dt(row.get("best_datetime_utc")),
                            _parse_dt(row.get("best_datetime_local")),
                            _parse_float(row.get("best_altitude_deg")),
                            _parse_float(row.get("best_apmag")),
                            _parse_float(row.get("solar_elong_deg")),
                            int(row.get("score", 0)),
                            row.get("rating", "unscored"),
                            bool(row.get("amateur_chaseable", False)),
                            row.get("source", "computed"),
                            row.get("calc_status", "unknown"),
                            row.get("magnitude_note"),
                        ),
                    )
                elif table == "lunar_occultations":
                    cur.execute("INSERT INTO paa.lunar_occultations VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (run_id, _parse_dt(row["datetime_local"]), row["target"], _parse_float(row.get("target_mag")), _parse_float(row.get("moon_altitude_deg")), row.get("limb"), row.get("event_type"), bool(row.get("is_planetary", False)), row["score"]))
                elif table == "meteor_showers":
                    cur.execute("INSERT INTO paa.meteor_showers VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (run_id, row["id"], row["name"], row["peak_date_local"], float(row["radiant_alt_peak_deg"]), float(row["radiant_alt_predawn_deg"]), float(row["moon_illumination_fraction"]), float(row["zhr"]), int(row["score"]), row["rating"], row.get("notes")))
                elif table == "conjunctions":
                    cur.execute(
                        "INSERT INTO paa.conjunctions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            run_id,
                            row["date_local"],
                            row["event_type"],
                            row["primary_body"],
                            row["secondary_body"],
                            float(row["separation_deg"]),
                            _parse_dt(row["event_time_local"]),
                            float(row["alt_primary_deg"]),
                            float(row["alt_secondary_deg"]),
                            float(row["sun_altitude_deg"]),
                            float(row["solar_elong_deg"]),
                            float(row["moon_illumination_fraction"]),
                            row["visibility_rating"],
                            int(row["score"]),
                            bool(row.get("is_solar_transit", False)),
                            row.get("safety_note"),
                        ),
                    )
                elif table == "ui_notes":
                    cur.execute(
                        "INSERT INTO paa.ui_notes VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (
                            run_id,
                            row["note_id"],
                            row["section"],
                            row["title"],
                            row["body"],
                            row.get("score", "info"),
                            row.get("date_local") or None,
                        ),
                    )
                else:
                    raise ValueError(f"Unknown table: {table}")
