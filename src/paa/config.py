from __future__ import annotations

from pathlib import Path

import yaml

from paa.models import Site


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_sites(path: Path) -> list[Site]:
    data = load_yaml(path)
    raw_sites = data.get("sites", [])
    if not isinstance(raw_sites, list):
        raise ValueError("sites.yaml must contain a list under 'sites'")
    return [Site(**item) for item in raw_sites]


def get_site(sites: list[Site], site_id: str) -> Site:
    for site in sites:
        if site.id == site_id:
            return site
    raise ValueError(f"Unknown site id: {site_id}")
