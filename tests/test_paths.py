import json
from pathlib import Path, PurePosixPath

import pytest

from paa.io.provenance import write_run_manifest
from paa.paths import (
    occult_cache_dir,
    public_data_path,
    public_month_path,
    public_site_slug,
    public_site_year_path,
    resolve_occult_cache_dir,
    resolve_site_year_dir,
    site_id_from_public_slug,
    site_year_dir,
)


def test_canonical_site_year_path() -> None:
    assert site_year_dir(Path("output"), "se_qld", 2027) == Path("output/se_qld/2027")
    assert occult_cache_dir(Path("output"), "se_qld", 2027) == Path(
        "output/se_qld/2027/cache/occult"
    )


@pytest.mark.parametrize(
    ("site_id", "slug"),
    [
        ("se_qld", "se-qld"),
        ("southern_tasmania", "southern-tasmania"),
        ("malabar_coast", "malabar-coast"),
    ],
)
def test_public_site_slugs_are_stable_and_reversible(site_id: str, slug: str) -> None:
    assert public_site_slug(site_id) == slug
    assert site_id_from_public_slug(slug) == site_id


def test_public_paths_use_the_published_posix_contract() -> None:
    assert public_site_year_path("se_qld", 2027) == PurePosixPath(
        "sites/se-qld/2027/index.html"
    )
    assert public_month_path("southern_tasmania", 2027, 3) == PurePosixPath(
        "sites/southern-tasmania/2027/months/03.html"
    )
    assert public_data_path("malabar_coast", 2027) == PurePosixPath(
        "sites/malabar-coast/2027/data/index.html"
    )


def test_public_paths_reject_unknown_sites_and_invalid_dates() -> None:
    with pytest.raises(ValueError, match="No public slug"):
        public_site_year_path("unconfigured", 2027)
    with pytest.raises(ValueError, match="publication year"):
        public_site_year_path("se_qld", 27)
    with pytest.raises(ValueError, match="publication month"):
        public_month_path("se_qld", 2027, 13)


def test_resolver_prefers_canonical_then_falls_back_to_legacy(tmp_path: Path) -> None:
    output = tmp_path / "output"
    legacy_data = output / "2027" / "data"
    legacy_data.mkdir(parents=True)
    manifest = output / "2027" / "logs" / "run_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"site_id": "se_qld"}), encoding="utf-8")
    assert resolve_site_year_dir(output, "se_qld", 2027, required="data") == output / "2027"

    current_data = output / "se_qld" / "2027" / "data"
    current_data.mkdir(parents=True)
    assert resolve_site_year_dir(output, "se_qld", 2027, required="data") == (
        output / "se_qld" / "2027"
    )


def test_resolver_rejects_legacy_data_from_another_site(tmp_path: Path) -> None:
    output = tmp_path / "output"
    legacy_data = output / "2027" / "data"
    legacy_data.mkdir(parents=True)
    manifest = output / "2027" / "logs" / "run_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"site_id": "southern_tasmania"}), encoding="utf-8")

    assert resolve_site_year_dir(output, "se_qld", 2027, required="data") == (
        output / "se_qld" / "2027"
    )


def test_occult_resolver_supports_old_site_nesting(tmp_path: Path) -> None:
    legacy = tmp_path / "output" / "2027" / "cache" / "occult" / "se_qld"
    legacy.mkdir(parents=True)
    assert resolve_occult_cache_dir(tmp_path / "output", "se_qld", 2027) == legacy


def test_site_ids_cannot_escape_output_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid site id"):
        site_year_dir(tmp_path, "../elsewhere", 2027)


def test_run_manifest_is_written_to_canonical_site_tree(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    for name in ("sites.yaml", "almanac.yaml", "horizons_objects.yaml", "meteor_showers.yaml"):
        (config / name).write_text("fixture: true\n", encoding="utf-8")

    manifest = write_run_manifest(2027, "se_qld", config, tmp_path / "output")

    assert manifest == tmp_path / "output" / "se_qld" / "2027" / "logs" / "run_manifest.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["site_id"] == "se_qld"
