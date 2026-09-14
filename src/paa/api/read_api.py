from __future__ import annotations

import os

from fastapi import FastAPI
import psycopg


app = FastAPI(title="personal-astro-almanac API", version="0.1.0")


def _db_url() -> str:
    url = os.getenv("PAA_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set PAA_DATABASE_URL")
    return url


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/runs")
def runs() -> list[dict]:
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT run_id, year, site_id, built_at FROM paa.runs ORDER BY run_id DESC LIMIT 20")
            rows = cur.fetchall()
    return [{"run_id": r[0], "year": r[1], "site_id": r[2], "built_at": r[3].isoformat()} for r in rows]


@app.get("/meteor-showers/{run_id}")
def meteor_showers(run_id: int) -> list[dict]:
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,name,peak_date_local,radiant_alt_predawn_deg,moon_illumination_fraction,score,rating FROM paa.meteor_showers WHERE run_id=%s ORDER BY peak_date_local",
                (run_id,),
            )
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "peak_date_local": str(r[2]),
            "radiant_alt_predawn_deg": r[3],
            "moon_illumination_fraction": r[4],
            "score": r[5],
            "rating": r[6],
        }
        for r in rows
    ]
