from __future__ import annotations

import json
from pathlib import Path

import requests

SBDB_QUERY_API = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"


def query_comet_candidates(limit: int = 500, cache_path: Path | None = None) -> list[dict]:
    # Pull broad comet list; we keep this permissive and filter locally.
    if cache_path is not None and cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        params = {
            "sb-kind": "c",
            "fields": "pdes,full_name,spkid,e,a,q,i,om,w,tp,per,moid_jup,moid,M1,K1",
            "limit": str(limit),
        }
        r = requests.get(SBDB_QUERY_API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    fields = data.get("fields", [])
    rows = data.get("data", [])
    out: list[dict] = []
    for row in rows:
        item = {fields[i]: row[i] if i < len(row) else None for i in range(len(fields))}
        out.append(item)
    return out
