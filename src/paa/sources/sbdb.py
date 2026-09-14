from __future__ import annotations

import requests


SBDB_QUERY_API = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"


def query_comet_candidates(limit: int = 500) -> list[dict]:
    # Pull broad comet list; we keep this permissive and filter locally.
    params = {
        "sb-kind": "c",
        "fields": "pdes,full_name,e,a,q,i,om,w,tp,per,moid_jup,moid",
        "limit": str(limit),
    }
    r = requests.get(SBDB_QUERY_API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    fields = data.get("fields", [])
    rows = data.get("data", [])
    out: list[dict] = []
    for row in rows:
        item = {fields[i]: row[i] if i < len(row) else None for i in range(len(fields))}
        out.append(item)
    return out
