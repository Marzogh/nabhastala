from __future__ import annotations

import json
import re
from pathlib import Path

_SITE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate_site_id(site_id: str) -> str:
    """Return a filesystem-safe configured site id."""
    if not _SITE_ID.fullmatch(site_id):
        raise ValueError(f"Invalid site id: {site_id!r}")
    return site_id


def site_year_dir(output_dir: Path, site_id: str, year: int) -> Path:
    """Canonical write location for one site's annual outputs."""
    return output_dir / validate_site_id(site_id) / str(year)


def legacy_year_dir(output_dir: Path, year: int) -> Path:
    """Pre-multi-site output location, supported for reads only."""
    return output_dir / str(year)


def _legacy_matches_site(root: Path, site_id: str) -> bool:
    """Require provenance before treating a legacy tree as a site's data."""
    manifest = root / "logs" / "run_manifest.json"
    if not manifest.exists():
        return False
    try:
        content = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return content.get("site_id") == site_id


def resolve_site_year_dir(
    output_dir: Path,
    site_id: str,
    year: int,
    *,
    required: str | Path | None = None,
) -> Path:
    """Prefer the canonical location, falling back to a usable legacy tree.

    The returned legacy path must only be used as a read source. All callers that
    write output should use :func:`site_year_dir` directly.
    """
    preferred = site_year_dir(output_dir, site_id, year)
    legacy = legacy_year_dir(output_dir, year)
    suffix = Path(required) if required is not None else None

    def usable(root: Path) -> bool:
        return (root / suffix).exists() if suffix is not None else root.exists()

    if usable(preferred):
        return preferred
    if usable(legacy) and _legacy_matches_site(legacy, site_id):
        return legacy
    return preferred


def occult_cache_dir(output_dir: Path, site_id: str, year: int) -> Path:
    return site_year_dir(output_dir, site_id, year) / "cache" / "occult"


def resolve_occult_cache_dir(output_dir: Path, site_id: str, year: int) -> Path:
    preferred = occult_cache_dir(output_dir, site_id, year)
    if preferred.exists():
        return preferred
    legacy = legacy_year_dir(output_dir, year) / "cache" / "occult" / validate_site_id(site_id)
    return legacy if legacy.exists() else preferred
