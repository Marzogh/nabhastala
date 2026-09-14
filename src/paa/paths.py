from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

_SITE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

PUBLIC_SITE_SLUGS = {
    "se_qld": "se-qld",
    "southern_tasmania": "southern-tasmania",
    "malabar_coast": "malabar-coast",
}
_SITE_IDS_BY_PUBLIC_SLUG = {slug: site_id for site_id, slug in PUBLIC_SITE_SLUGS.items()}


def validate_site_id(site_id: str) -> str:
    """Return a filesystem-safe configured site id."""
    if not _SITE_ID.fullmatch(site_id):
        raise ValueError(f"Invalid site id: {site_id!r}")
    return site_id


def public_site_slug(site_id: str) -> str:
    """Return the stable URL slug for a configured observing site."""
    try:
        return PUBLIC_SITE_SLUGS[site_id]
    except KeyError as error:
        raise ValueError(f"No public slug for site id: {site_id!r}") from error


def site_id_from_public_slug(slug: str) -> str:
    """Return the configured site id represented by a stable URL slug."""
    try:
        return _SITE_IDS_BY_PUBLIC_SLUG[slug]
    except KeyError as error:
        raise ValueError(f"Unknown public site slug: {slug!r}") from error


def _validate_public_year(year: int) -> int:
    if not 1000 <= year <= 9999:
        raise ValueError(f"Invalid publication year: {year!r}")
    return year


def public_site_year_path(site_id: str, year: int) -> PurePosixPath:
    """Return the stable published annual index path, independent of host OS."""
    return (
        PurePosixPath("sites")
        / public_site_slug(site_id)
        / str(_validate_public_year(year))
        / "index.html"
    )


def public_month_path(site_id: str, year: int, month: int) -> PurePosixPath:
    """Return the stable published path for one monthly field guide."""
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid publication month: {month!r}")
    return public_site_year_path(site_id, year).parent / "months" / f"{month:02d}.html"


def public_data_path(site_id: str, year: int) -> PurePosixPath:
    """Return the stable published dataset-library path for a site and year."""
    return public_site_year_path(site_id, year).parent / "data" / "index.html"


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
