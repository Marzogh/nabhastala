from __future__ import annotations

import hashlib
import json
import posixpath
import re
import shutil
from datetime import UTC, datetime
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from paa.paths import public_site_slug, site_year_dir
from paa.validate.reports import validation_failures

PUBLIC_BASE_URL = "https://chipsncode.com/nabhastala"
PUBLISH_DIRECTORIES = ("assets", "charts", "data", "months", "sky")
LINK_ATTRIBUTE = re.compile(
    r'(?P<prefix>\b(?:href|src|data-source|data-moon-src)=["\'])'
    r'(?P<url>[^"\']+)(?P<quote>["\'])'
)
CSS_URL = re.compile(r"url\((?P<quote>['\"]?)(?P<url>[^)'\"]+)(?P=quote)\)")
FORBIDDEN_PARTS = {"cache", "logs", "_sources", ".git", ".env"}
FORBIDDEN_NAMES = {"id_rsa", "id_ed25519", "credentials", "secrets"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalise_local_target(source_file: PurePosixPath, raw_path: str) -> PurePosixPath:
    joined = posixpath.normpath(
        posixpath.join("/", str(source_file.parent), raw_path)
        if not raw_path.startswith("/")
        else raw_path
    )
    return PurePosixPath(joined.lstrip("/"))


def _map_public_target(
    target: PurePosixPath,
    *,
    site_ids: tuple[str, ...],
) -> PurePosixPath:
    parts = target.parts
    if len(parts) >= 3 and parts[0] in site_ids and parts[1].isdigit():
        suffix = list(parts[2:])
        if suffix == ["almanac.html"]:
            suffix = ["index.html"]
        return PurePosixPath("sites", public_site_slug(parts[0]), parts[1], *suffix)
    if parts and parts[0] == "pdf":
        return PurePosixPath("downloads", *parts[1:])
    return target


def _rewrite_url(
    raw_url: str,
    *,
    source_file: PurePosixPath,
    destination_file: PurePosixPath,
    site_ids: tuple[str, ...],
) -> str:
    parsed = urlsplit(raw_url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return raw_url
    source_target = _normalise_local_target(source_file, parsed.path)
    public_target = _map_public_target(source_target, site_ids=site_ids)
    relative = posixpath.relpath(str(public_target), str(destination_file.parent) or ".")
    if parsed.path.endswith("/") and not relative.endswith("/"):
        relative += "/"
    return urlunsplit(("", "", relative, parsed.query, parsed.fragment))


def _canonical_url(path: PurePosixPath, base_url: str) -> str:
    clean = str(path)
    if path.name == "index.html":
        parent = str(path.parent)
        clean = "" if parent == "." else parent.rstrip("/") + "/"
    return f"{base_url.rstrip('/')}/{clean.lstrip('/')}"


def _prepare_html(
    text: str,
    *,
    source_file: PurePosixPath,
    destination_file: PurePosixPath,
    site_ids: tuple[str, ...],
    base_url: str,
) -> str:
    def replace(match: re.Match[str]) -> str:
        rewritten = _rewrite_url(
            match.group("url"),
            source_file=source_file,
            destination_file=destination_file,
            site_ids=site_ids,
        )
        return f'{match.group("prefix")}{rewritten}{match.group("quote")}'

    result = LINK_ATTRIBUTE.sub(replace, text)
    canonical = escape(_canonical_url(destination_file, base_url), quote=True)
    metadata = f'    <link rel="canonical" href="{canonical}">\n'
    return result.replace("  </head>", f"{metadata}  </head>", 1)


def _copy_html(
    source: Path,
    destination: Path,
    *,
    source_virtual: PurePosixPath,
    destination_virtual: PurePosixPath,
    site_ids: tuple[str, ...],
    base_url: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        _prepare_html(
            source.read_text(encoding="utf-8"),
            source_file=source_virtual,
            destination_file=destination_virtual,
            site_ids=site_ids,
            base_url=base_url,
        ),
        encoding="utf-8",
    )


def _copy_directory(
    source: Path,
    destination: Path,
    *,
    source_virtual_root: PurePosixPath,
    destination_virtual_root: PurePosixPath,
    site_ids: tuple[str, ...],
    base_url: str,
) -> None:
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        if path.suffix.lower() == ".html":
            _copy_html(
                path,
                target,
                source_virtual=source_virtual_root / PurePosixPath(relative.as_posix()),
                destination_virtual=(
                    destination_virtual_root / PurePosixPath(relative.as_posix())
                ),
                site_ids=site_ids,
                base_url=base_url,
            )
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _write_sitemap(root: Path, base_url: str) -> None:
    urls = []
    for path in sorted(root.rglob("*.html")):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        urls.append(_canonical_url(relative, base_url))
    entries = "".join(f"  <url><loc>{escape(url)}</loc></url>\n" for url in urls)
    (root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n",
        encoding="utf-8",
    )
    (root / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base_url.rstrip('/')}/sitemap.xml\n",
        encoding="utf-8",
    )


def _write_release_manifest(
    root: Path,
    *,
    years: tuple[int, ...],
    site_ids: tuple[str, ...],
    base_url: str,
) -> None:
    hashes = {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "release.json"
    }
    (root / "release.json").write_text(
        json.dumps(
            {
                "assembled_at_utc": datetime.now(UTC).isoformat(),
                "base_url": base_url,
                "years": list(years),
                "sites": list(site_ids),
                "files_sha256": hashes,
                "scientific_recomputation": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _internal_target(root: Path, source: Path, raw_url: str) -> Path | None:
    parsed = urlsplit(raw_url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    target = (source.parent / parsed.path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"Link escapes release tree: {source}: {raw_url}") from error
    if parsed.path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target


def validate_release_tree(destination: Path) -> list[str]:
    """Return release errors without modifying the assembled tree."""
    root = destination.resolve()
    errors: list[str] = []
    required = ("index.html", ".nojekyll", "sitemap.xml", "robots.txt", "release.json")
    for name in required:
        if not (root / name).is_file():
            errors.append(f"missing required release file: {name}")

    for path in sorted(root.rglob("*")) if root.exists() else ():
        relative = path.relative_to(root)
        lowered_parts = {part.lower() for part in relative.parts}
        if lowered_parts & FORBIDDEN_PARTS:
            errors.append(f"forbidden release path: {relative.as_posix()}")
        if path.name.lower() in FORBIDDEN_NAMES:
            errors.append(f"possible credential file: {relative.as_posix()}")
        if path.is_symlink():
            errors.append(f"symbolic link is not publishable: {relative.as_posix()}")
        if path.is_file() and path.stat().st_size >= 100 * 1024 * 1024:
            errors.append(f"file exceeds GitHub's 100 MB limit: {relative.as_posix()}")
        if not path.is_file() or path.suffix.lower() not in {".html", ".css"}:
            continue
        text = path.read_text(encoding="utf-8")
        urls = (
            [match.group("url") for match in LINK_ATTRIBUTE.finditer(text)]
            if path.suffix.lower() == ".html"
            else [match.group("url") for match in CSS_URL.finditer(text)]
        )
        for raw_url in urls:
            if raw_url.startswith(("#", "data:")):
                continue
            try:
                target = _internal_target(root, path, raw_url)
            except ValueError as error:
                errors.append(str(error))
                continue
            if target is not None and not target.exists():
                errors.append(
                    f"missing internal target: {relative.as_posix()} -> {raw_url}"
                )
    return sorted(set(errors))


def assemble_release(
    *,
    years: tuple[int, ...],
    site_ids: tuple[str, ...],
    output_dir: Path,
    destination: Path,
    base_url: str = PUBLIC_BASE_URL,
) -> Path:
    """Assemble validated local artifacts without recalculating astronomy."""
    if not years or not site_ids:
        raise ValueError("At least one year and site are required")
    for year in years:
        for site_id in site_ids:
            failures = validation_failures(year, site_id, output_dir)
            if failures:
                raise ValueError(
                    f"Validation failed for {site_id} {year}: {', '.join(failures)}"
                )
            edition = site_year_dir(output_dir, site_id, year)
            if not (edition / "almanac.html").is_file():
                raise ValueError(f"Rendered HTML is missing for {site_id} {year}")
            missing_directories = [
                name for name in PUBLISH_DIRECTORIES if not (edition / name).is_dir()
            ]
            if missing_directories:
                raise ValueError(
                    f"Rendered directories are missing for {site_id} {year}: "
                    + ", ".join(missing_directories)
                )
            pdf = output_dir / "pdf" / (
                f"nabhastala-{year}-{public_site_slug(site_id)}-field-edition.pdf"
            )
            if not pdf.is_file():
                raise ValueError(f"Field PDF is missing for {site_id} {year}: {pdf}")

    staging = destination.parent / f".{destination.name}-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    (staging / ".nojekyll").write_text("", encoding="utf-8")

    _copy_directory(
        output_dir / "assets",
        staging / "assets",
        source_virtual_root=PurePosixPath("assets"),
        destination_virtual_root=PurePosixPath("assets"),
        site_ids=site_ids,
        base_url=base_url,
    )
    _copy_html(
        output_dir / "index.html",
        staging / "index.html",
        source_virtual=PurePosixPath("index.html"),
        destination_virtual=PurePosixPath("index.html"),
        site_ids=site_ids,
        base_url=base_url,
    )

    for year in years:
        for site_id in site_ids:
            source_root = site_year_dir(output_dir, site_id, year)
            public_root = PurePosixPath("sites", public_site_slug(site_id), str(year))
            target_root = staging / Path(public_root.as_posix())
            for directory in PUBLISH_DIRECTORIES:
                _copy_directory(
                    source_root / directory,
                    target_root / directory,
                    source_virtual_root=PurePosixPath(site_id, str(year), directory),
                    destination_virtual_root=public_root / directory,
                    site_ids=site_ids,
                    base_url=base_url,
                )
            _copy_html(
                source_root / "almanac.html",
                target_root / "index.html",
                source_virtual=PurePosixPath(site_id, str(year), "almanac.html"),
                destination_virtual=public_root / "index.html",
                site_ids=site_ids,
                base_url=base_url,
            )
            pdf_name = (
                f"nabhastala-{year}-{public_site_slug(site_id)}-field-edition.pdf"
            )
            (staging / "downloads").mkdir(exist_ok=True)
            shutil.copy2(output_dir / "pdf" / pdf_name, staging / "downloads" / pdf_name)

    _write_sitemap(staging, base_url)
    _write_release_manifest(
        staging,
        years=years,
        site_ids=site_ids,
        base_url=base_url,
    )
    errors = validate_release_tree(staging)
    if errors:
        raise ValueError("Release validation failed:\n" + "\n".join(errors))
    if destination.exists():
        shutil.rmtree(destination)
    staging.replace(destination)
    return destination
