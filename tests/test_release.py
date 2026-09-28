from pathlib import Path

import pytest

import paa.release as release_module
from paa.release import assemble_release, validate_release_tree


def _write(path: Path, content: str = "fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _release_fixture(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    _write(
        output / "index.html",
        '<html><head>  </head><body><a href="se_qld/2026/almanac.html">Edition</a>'
        '<link href="assets/site.css"></body></html>',
    )
    _write(output / "assets" / "site.css", 'body{background:url("art/paper.webp")}')
    _write(output / "assets" / "art" / "paper.webp")
    edition = output / "se_qld" / "2026"
    _write(
        edition / "almanac.html",
        '<html><head>  </head><body><a href="../../index.html">Home</a>'
        '<a href="months/01.html">January</a>'
        '<a href="../../pdf/nabhastala-2026-se-qld-field-edition.pdf">PDF</a>'
        '<script src="assets/site.js"></script></body></html>',
    )
    _write(
        edition / "months" / "01.html",
        '<html><head>  </head><body><a href="../almanac.html">Annual</a></body></html>',
    )
    _write(edition / "data" / "index.html", '<html><head>  </head><body></body></html>')
    _write(edition / "data" / "sun_twilight.csv", "date\n2026-01-01\n")
    _write(edition / "sky" / "index.html", '<html><head>  </head><body></body></html>')
    _write(edition / "assets" / "site.js", "void 0;")
    _write(edition / "charts" / "sky" / "month-01.svg", "<svg></svg>")
    _write(edition / "cache" / "private-source.txt", "must not publish")
    _write(edition / "logs" / "run.log", "must not publish")
    _write(output / "pdf" / "nabhastala-2026-se-qld-field-edition.pdf", "%PDF")
    return output


def test_release_assembles_stable_routes_without_private_build_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = _release_fixture(tmp_path)
    monkeypatch.setattr(release_module, "validation_failures", lambda *_: [])

    destination = assemble_release(
        years=(2026,),
        site_ids=("se_qld",),
        output_dir=output,
        destination=tmp_path / "site",
    )

    annual = destination / "sites" / "se-qld" / "2026" / "index.html"
    month = destination / "sites" / "se-qld" / "2026" / "months" / "01.html"
    assert annual.is_file()
    assert '../../../index.html' in annual.read_text(encoding="utf-8")
    assert '../../../downloads/nabhastala-2026-se-qld-field-edition.pdf' in annual.read_text(
        encoding="utf-8"
    )
    assert '../index.html' in month.read_text(encoding="utf-8")
    assert 'href="sites/se-qld/2026/index.html"' in (
        destination / "index.html"
    ).read_text(encoding="utf-8")
    assert 'rel="canonical"' in annual.read_text(encoding="utf-8")
    assert (
        'href="https://marzogh.github.io/nabhastala/"'
        in (destination / "index.html").read_text(encoding="utf-8")
    )
    assert not list(destination.rglob("cache"))
    assert not list(destination.rglob("logs"))
    assert validate_release_tree(destination) == []


def test_release_validator_reports_missing_internal_targets(tmp_path: Path) -> None:
    root = tmp_path / "site"
    _write(root / ".nojekyll", "")
    _write(root / "sitemap.xml", "<urlset></urlset>")
    _write(root / "robots.txt", "User-agent: *")
    _write(root / "release.json", "{}")
    _write(
        root / "index.html",
        '<html><body><a href="missing/page.html">Missing</a></body></html>',
    )

    errors = validate_release_tree(root)

    assert any("missing internal target" in error for error in errors)
