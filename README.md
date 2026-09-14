# नभस्तल — Nabhastala

**त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)**
**One sky at three horizons.**

Local, reproducible annual astronomy and astrophotography almanac generator.

Nabhastala is being developed as a static field almanac published independently
and linked from Chips’nCode. The Python distribution retains the technical name
`personal-astro-almanac`. See
[`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) for the current
restart-safe implementation stage.

## What it does

Generates a full-year observing/imaging dataset for a configured site, persists all results to PostgreSQL, and renders annual + monthly HTML and PDF outputs.

## Milestone status

- 0: project skeleton
- 1: Sun/Moon/dark windows
- 2: Milky Way planner
- 3: planetary visibility
- 4: Jupiter/Saturn moon offsets + charts
- 5: minor planets + comet catalog/opportunities
- 6: lunar occultation import/scoring
- 7: meteor shower local-usefulness scoring
- 8: annual index + monthly pages + validation report
- 9: PDF render
- 10-15: DB hardening, reproducibility manifest, portability scaffolding, API-readiness, CI workflow

## Quickstart (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run the baseline test suite from the repository root:

```bash
python -m pytest
```

## Database

Set a PostgreSQL URL (required for build):

```bash
export PAA_DATABASE_URL='postgresql://postgres:postgres@localhost:55432/astro'
astro-almanac db-init
astro-almanac db-check
```

You can run PostgreSQL quickly with Docker:

```bash
docker compose up -d postgres
```

## Main workflow

```bash
astro-almanac init-config --output config
astro-almanac import-occult --year 2027 --site se_qld --file /path/to/occult_export.csv
astro-almanac build --year 2027 --site se_qld --config-dir config
astro-almanac render --year 2027 --site se_qld --format html
astro-almanac render --year 2027 --site se_qld --format pdf
astro-almanac view --2027
```

Outputs:

- `output/<site>/<year>/data/*.csv`
- `output/<site>/<year>/charts/*`
- `output/<site>/<year>/almanac.html`
- `output/<site>/<year>/almanac.pdf`
- `output/<site>/<year>/months/*.html`
- `output/<site>/<year>/logs/validation_report.md`
- `output/<site>/<year>/logs/run_manifest.json`

Existing `output/<year>/` trees are supported as read-only legacy inputs. New
commands never write to the legacy layout.

## API (read-only)

Run locally:

```bash
uvicorn paa.api.read_api:app --reload
```

Endpoints:

- `GET /health`
- `GET /runs`
- `GET /meteor-showers/{run_id}`
