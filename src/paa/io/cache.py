from __future__ import annotations

import hashlib
from pathlib import Path


def query_hash(parts: dict[str, str]) -> str:
    joined = "&".join(f"{k}={parts[k]}" for k in sorted(parts))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def cache_path(base: Path, year: int, source: str, scope: str, key: str, ext: str) -> Path:
    return base / str(year) / "cache" / source / scope / f"{key}.{ext}"


def write_cache_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
