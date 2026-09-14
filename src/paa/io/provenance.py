from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from paa.paths import site_year_dir


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b = f.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def write_run_manifest(year: int, site_id: str, config_dir: Path, output_dir: Path, run_id: int | None = None) -> Path:
    files = [
        config_dir / 'sites.yaml',
        config_dir / 'almanac.yaml',
        config_dir / 'horizons_objects.yaml',
        config_dir / 'meteor_showers.yaml',
    ]
    manifest = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'year': year,
        'site_id': site_id,
        'run_id': run_id,
        'config_hashes': {p.name: _sha256(p) for p in files if p.exists()},
        'generator': 'personal-astro-almanac',
        'author': 'Prajwal Bhattaram',
    }
    out = site_year_dir(output_dir, site_id, year) / 'logs' / 'run_manifest.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
    return out
