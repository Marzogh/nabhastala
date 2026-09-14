# Nabhastala architecture

Nabhastala is a local astronomy-data generator with a separately assembled static
publication. Scientific computation stays in Python; the published site contains
only reviewed HTML, CSS, minimal progressive-enhancement JavaScript, images, CSV
downloads, and a curated PDF.

## Boundaries

- `src/paa/compute/` owns astronomy calculations and scoring.
- `src/paa/render/` owns view models, HTML templates, and PDF composition.
- `output/` contains local, reproducible scientific build products and is not committed.
- `site/` contains reviewed release artifacts and is committed for GitHub Pages.
- Published pages never require PostgreSQL, Python, or network access at runtime.

New scientific builds will eventually use `output/<site>/<year>/`. Renderers will
retain read-only support for the legacy `output/<year>/` layout.

## Public identity

The following wording is immutable unless its owner supplies a replacement:

> नभस्तल  
> Nabhastala  
> त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)  
> One sky at three horizons.

The visual system follows the shared Chips’nCode typography, colour, spacing,
navigation, and accessibility principles while allowing astronomy-specific views
where the data requires them.

## Release rule

Astronomy data is generated and validated locally. A release command will later
assemble approved outputs into `site/`. GitHub Actions will validate and deploy
those committed bytes; it will not recompute astronomy data.

