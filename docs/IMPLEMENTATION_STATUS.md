# Nabhastala implementation status

This file is the restart point for the staged redesign. Do not begin a new stage
until the previous stage is committed, tagged, and marked complete here.

## Current stage

- Stage: 5D, interactive date-and-time sky chart
- State: complete
- Objective: add a site-aware chart for any date and local time in the edition,
  backed entirely by locally generated annual data
- Started: 2026-09-29

## Stage 5D: Interactive date-and-time sky chart

Affected files:

- `src/paa/render/sky_charts.py`
- `src/paa/render/html.py`
- `src/paa/render/templates/sky.html`
- `src/paa/render/templates/base.html`
- `src/paa/render/templates/monthly.html`
- `src/paa/render/static/sky.js`
- `src/paa/render/static/editorial.css`
- `src/paa/render/static/styles.css`
- `src/paa/render/almanac_views.py`
- `src/paa/render/view_models.py`
- focused sky-chart and navigation tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- A visitor can choose any date and local time within the edition year and see
  an immediate all-sky chart for the selected horizon.
- The chart includes naked-eye stars, constellation figures, named bright
  stars, the Sun, Moon and planets where they are above the horizon.
- Date conversion respects each edition's named time zone, including daylight
  saving changes, rather than the visitor's computer time zone.
- All runtime astronomy is limited to coordinate projection over data generated
  on the Mac. The published page makes no astronomy-service requests.
- The chart is keyboard operable, responsive, printable and still links to the
  twelve static monthly charts when JavaScript is unavailable.
- Compass bearings include intercardinal points, 5-degree ticks and numbered
  30-degree intervals. Constellation stars, field stars, planets and the Moon
  remain distinguishable in light and dark themes and in monochrome print.
- Lunar samples use curved waxing and waning geometry rather than percentage
  blocks, and remain legible in light, dark and monochrome print output.
- All three editions render, local links resolve and regression tests pass.

Exact resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_sky_charts.py tests/test_brand_shell.py tests/test_information_architecture.py
PYTHONPATH=src .venv/bin/astro-almanac render --year 2026 --site se_qld --format html
```

Results:

- Added a dedicated Sky page with local date and time controls, a limiting-
  magnitude control, optional constellation figures, visible-object readout,
  current-time shortcut and print action.
- Generated a compact annual browser dataset for each horizon from the locally
  cached Hipparcos catalogue and JPL ephemeris. Browser interaction performs
  only coordinate projection and makes no astronomy-service request.
- Added complete compass graduations, named bright stars, distinct field and
  constellation stars, and deliberate light and dark palettes for every Solar
  System object. Monochrome print uses outlines, fills and direct labels.
- Current conditions now lead with a plain-language observing verdict while
  retaining the individual measurements below it.
- Replaced the clipped lunar phase blocks with accurately directed, curved
  waxing and waning SVG silhouettes.
- Regenerated and validated all three 2026 editions. Interactive and monthly
  pages were visually checked in light and dark themes.
- Focused checks: 18 passed. Full regression suite: 79 passed. All three data
  editions validated. Changed-file Ruff checks, JavaScript syntax checks and
  `git diff --check` passed.
- Checkpoint tag: `stage-5d-interactive-sky-chart`.

## Stage 5C: Monthly sky charts and observing conditions

Affected files:

- `src/paa/render/sky_charts.py`
- `src/paa/render/html.py`
- `src/paa/render/templates/monthly.html`
- `src/paa/render/static/conditions.js`
- `src/paa/render/static/editorial.css`
- focused chart and renderer tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Each site and month receives an all-sky orientation chart calculated locally
  for 10 pm on the middle night of the month.
- Bright stars, constellation lines, cardinal directions and visible planets
  remain legible in light and dark themes and when printed.
- The monthly page shows current cloud, rain, wind, visibility and air-quality
  measurements when the free source is reachable, without blocking the static
  almanac when it is not.
- Public copy describes observing conditions directly and contains no source,
  build-pipeline or implementation commentary.
- All three editions render and the focused and regression tests pass.

Exact resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_sky_charts.py tests/test_html_render.py
PYTHONPATH=src .venv/bin/astro-almanac render --year 2026 --site se_qld --format html
```

Results:

- Generated 36 site-specific all-sky SVG charts from the cached Hipparcos
  catalogue, JPL ephemeris and constellation figures. Each chart shows the sky
  at 10 pm on the middle night of its month with cardinal directions, bright
  stars, constellation lines, labels, the Moon and visible planets.
- Charts respond to light and dark themes, remain readable in print, and are
  generated entirely on the Mac after the one-time constellation-file download.
- Added a concise current-conditions panel using Open-Meteo weather and air
  quality feeds. It reports cloud, rain, wind, visibility and fine particles,
  and fails quietly without hiding any almanac content.
- Verified the live panel and chart visually in light and dark themes. All 36
  production charts contain real constellation geometry rather than fixture
  placeholders.
- Focused renderer and chart tests: 16 passed. Full regression suite: 77 passed.
  Ruff, JavaScript syntax checking and `git diff --check` passed.
- Checkpoint tag: `stage-5c-sky-charts-conditions`.

## Stage 5B: Eclipses and planetary phenomena

Affected files:

- `src/paa/compute/phenomena.py`
- `src/paa/cli.py`
- `src/paa/render/almanac_views.py`
- `src/paa/render/html.py`
- `src/paa/validate/reports.py`
- focused phenomena and renderer tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Solar and lunar eclipse circumstances are calculated for each configured
  observing horizon using the cached JPL ephemeris.
- Mercury and Venus greatest elongations, outer-planet oppositions and planetary
  stationary dates are generated annually without model calls.
- Monthly and annual pages can rank useful phenomena without exposing internal
  calculation language.
- Complete phenomena remain downloadable as CSV and empty output fails validation.
- All three editions build, validate and render before the checkpoint.

Exact resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_phenomena.py tests/test_annual_overview.py tests/test_validation.py
PYTHONPATH=src .venv/bin/astro-almanac build --year 2026 --site se_qld --skip-db --sections phenomena --force
```

Results:

- Added annual, repeatable eclipse and planetary-event generation using the
  already cached JPL DE440s ephemeris. No model or remote service is involved.
- Generated 30 phenomena rows for each 2026 edition, including site-specific
  eclipse visibility and altitude, Mercury and Venus greatest elongations,
  outer-planet oppositions and planetary stationary dates.
- Confirmed the 3 March total lunar eclipse, 28 August partial lunar eclipse,
  10 January Jupiter opposition and 4 October Saturn opposition.
- Integrated useful events into annual and monthly rankings using concise
  observer-facing language. Complete source values remain downloadable in the
  data library.
- Empty phenomena output is now a validation failure. All three editions build,
  validate and render successfully.
- Focused tests: 10 passed. Full regression suite: 75 passed. Ruff and
  `git diff --check` passed.
- Checkpoint tag: `stage-5b-astronomical-phenomena`.

## Stage 5A2: Site-specific lunar occultations

Affected files:

- `src/paa/compute/occultations.py`
- `src/paa/sources/occult_import.py`
- `src/paa/cli.py`
- `src/paa/validate/reports.py`
- `config/almanac.yaml`
- focused occultation computation and validation tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- The annual builder produces non-empty, site-specific lunar occultation data
  for all three configured horizons without a manual import.
- JPL ephemeris and Hipparcos catalogue inputs are downloaded once, cached
  locally, and reused without network access.
- Predictions include local disappearance and reappearance times, target
  magnitude, Moon altitude and an explicit geometric prediction type.
- Events below the configured Moon-altitude threshold or outside the requested
  edition year are excluded.
- Australian bright-star events are cross-checked against published 2026
  Brisbane and Hobart tables generated with IOTA Occult 4.
- The public data states that timings use a smooth geometric lunar limb and are
  planning predictions, not graze-grade lunar-terrain predictions.
- Existing manual `import-occult` support and existing CSV columns remain valid.

Exact resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_occult_import.py tests/test_occultations.py tests/test_validation.py
PYTHONPATH=src .venv/bin/astro-almanac build --year 2026 --site se_qld --skip-db --sections occultations --force
```

Results:

- Added a repeatable local prediction engine using the cached JPL DE440s
  ephemeris and Hipparcos catalogue. The 83 MB source cache is reused across
  all sites and future builds without model calls.
- Generated 660 contact rows for South East Queensland, 636 for Southern
  Tasmania, and 629 for the Malabar Coast. Each contact includes local time,
  target magnitude where available, Moon altitude, contact type and rating.
- Included site-specific planetary events. Notable results include the 14
  September Venus occultation for the Malabar Coast and 3 November Jupiter
  occultations for all three horizons where locally observable.
- Cross-checked the 31 May Antares reappearance for Brisbane at 18:10 against
  the published Occult 4 table, with exact minute agreement. The Tasmania
  engine times of 01:57:44 and 03:00:38 for the 28 June Antares occultation
  round to the published Hobart times of 01:58 and 03:01.
- Preserved manual `import-occult` input as an authoritative override. Automated
  predictions run only when no imported site file is present.
- Monthly and annual views group disappearance and reappearance contacts into
  one observing opportunity and retain the complete contact data for download.
- Added the concise observer warning that timings use a smooth lunar limb and
  grazing events should be confirmed with IOTA Occult 4.
- Empty occultation output is now a validation failure. All three 2026 edition
  validation reports pass.
- Focused renderer and computation tests: 15 passed. Full regression suite: 72
  passed. Ruff and `git diff --check` passed for every affected file.
- Checkpoint tag: `stage-5a2-lunar-occultations`.

## Stage 5A1: Comet source repair

Affected files:

- `src/paa/compute/minor_planets.py`
- `src/paa/sources/horizons.py`
- `src/paa/sources/sbdb.py`
- `src/paa/cli.py`
- `src/paa/validate/reports.py`
- focused source, computation and validation tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Periodic and non-periodic comet designations resolve to a current integrated
  Horizons solution without manual record numbers.
- Horizons `T-mag`, `N-mag` and `APmag` outputs parse safely.
- Raw SBDB and Horizons responses are cached under the local edition.
- Missing magnitude is distinguished from query failure.
- A release fails when comet source queries fail beyond the allowed threshold.
- Existing CSV columns and non-comet computation remain compatible.

Exact resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_horizons_parser.py tests/test_minor_planets.py tests/test_validation.py
PYTHONPATH=src .venv/bin/astro-almanac build --year 2026 --site se_qld --skip-db --sections comets --force
```

Results:

- Replaced ambiguous bare periodic-comet queries with JPL Horizons current
  integrated-solution queries using `DES=<designation>;CAP`.
- Added safe parsing for Horizons `T-mag`, `N-mag` and `APmag` fields, while
  retaining a distinct state when no usable magnitude is supplied.
- Cached the SBDB catalogue and every Horizons response, including negative
  responses, under each local edition. All three annual comet builds now rerun
  offline in under two seconds combined.
- Generated 61 catalogue rows for each 2026 horizon. South East Queensland has
  9 potentially amateur-observable entries, Southern Tasmania has 8, and the
  Malabar Coast has 6 under the configured limits.
- JPL provides no complete 2026 ephemeris for `51P` and `57P`; these remain
  explicit isolated `query_failed` rows rather than silently disappearing.
- All three validation reports pass with 2 isolated source failures out of 61
  candidates. Validation now fails when more than half of comet queries fail.
- Focused tests: 9 passed. Full regression suite: 67 passed. Ruff passed for all
  affected Python and test files; `git diff --check` passed.
- Checkpoint tag: `stage-5a1-comet-source-repair`.

## Stage 5: Curated field PDF

Affected files:

- `src/paa/render/pdf.py`
- `src/paa/render/templates/field_pdf.html`
- `src/paa/render/static/field_pdf.css`
- `src/paa/cli.py`
- PDF-focused tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- A dedicated A4 print composition is used instead of printing the interactive site.
- Each edition contains annual priorities, a yearly index, twelve monthly field
  sheets, essential charting, field notes and source scope.
- Exhaustive daily and satellite-offset tables remain in the web edition only.
- Table headings repeat, pages do not clip, and ratings work in monochrome.
- All pages from all three PDFs are rendered to images and visually inspected.
- The focused and full regression test suites pass.

Exact resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/astro-almanac render --year 2026 --site se_qld --format pdf
find output/pdf -maxdepth 1 -type f -name '*.pdf' -print
```

Results:

- Replaced the full-page website print path with a dedicated Jinja and CSS A4
  field composition rendered locally by WeasyPrint. ReportLab is not used.
- Generated three 16-page 2026 field editions in `output/pdf/`, one for each
  configured observing horizon.
- Each edition contains the exact four-line identity, annual priority table,
  yearly index, a computed Galactic Centre time diagram, twelve monthly field
  sheets, concise interpretation notes, and source scope.
- Complete daily, satellite-offset and supporting tables remain in HTML and CSV
  instead of being repeated in the PDF.
- Every page from all three PDFs was rasterised and visually inspected. No
  clipping, blank pages, orphaned headings or unintended colour-only encoding
  was found.
- PDF structure checks confirmed A4 portrait pages, 16 pages per edition,
  extractable text on every page and all required sections.
- All three edition validation reports pass required datasets. Each retains the
  existing warning that no lunar-occultation rows are present.
- Focused PDF tests: 2 passed. Full regression suite: 62 passed. Ruff passed for
  all affected Python files; `git diff --check` passed. The repository-wide Ruff
  command still reports unrelated pre-existing issues outside Stage 5.
- Checkpoint tag: `stage-5-curated-field-pdf`.

## Stage 4A: Date-driven observing instruments

Implementation order:

1. Audit and correct the Moon-free interval calculation.
2. Generate full-year Jupiter and Saturn satellite tracks locally, using cached
   authoritative source responses.
3. Add a shared date-selected nightly planner and satellite chart that filter
   precomputed edition data in the browser.
4. Clarify that the annual Milky Way chart shows Galactic Centre visibility
   after darkness, Moon, and altitude constraints are applied.
5. Replace internal implementation copy, render locally, visually inspect, run
   focused and regression tests, then commit and tag the checkpoint.

Affected files:

- `src/paa/compute/sun_moon.py`
- `src/paa/compute/moons.py`
- `src/paa/sources/horizons.py`
- `src/paa/render/almanac_views.py`
- `src/paa/render/templates/annual.html`
- `src/paa/render/templates/monthly.html`
- `src/paa/render/templates/data_library.html`
- `src/paa/render/static/styles.css`
- `src/paa/render/static/charts.js`
- focused computation and renderer tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Every date in the edition can drive the nightly darkness display.
- Every date with observable Jupiter or Saturn data can drive its satellite plot.
- Satellite identity remains understandable without colour alone.
- The Galactic Centre chart states exactly which constraints it combines.
- Authoritative responses are downloaded and cached by local code without model
  calls; repeated builds reuse the cache.
- Existing CSV columns and commands remain compatible.
- Focused tests, full regression tests, local render, and visual inspection pass.

Focused test command:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_dark_windows.py tests/test_moons.py tests/test_monthly_guide.py tests/test_render_paths.py
```

Exact resume command:

```bash
git status --short
sed -n '/## Stage 4A:/,/## Stage 4:/p' docs/IMPLEMENTATION_STATUS.md
PYTHONPATH=src .venv/bin/pytest -q tests/test_dark_windows.py tests/test_moons.py tests/test_monthly_guide.py tests/test_render_paths.py
```

Results:

- Monthly pages now provide a date picker for every date in the month. The
  locally rendered view combines astronomical dusk and dawn, low-Moon darkness,
  usable Galactic Centre intervals, Moon rise/set and illumination, and daily
  planet samples.
- Moon rise and set events are evaluated chronologically across midnight. This
  fixes the former same-calendar-date pairing error in low-Moon intervals.
- Milky Way samples retain their observing-night date and are clamped to the
  source darkness interval. A pre-dawn sample can no longer appear outside the
  selected evening's displayed night.
- Jupiter and Saturn now have full-year locally generated JPL Horizons series:
  16,640 Jupiter rows and 12,654 Saturn rows for the reviewed 2026 SE Queensland
  edition. Raw source responses are cached locally and reused on rebuild.
- Satellite charts accept any edition date and clearly report dates with no
  observable nighttime samples. High-contrast colour, line patterns, points,
  direct labels, and a text key distinguish moons without relying on colour.
- Large satellite chart records are emitted as separate static JSON assets; the
  annual HTML remains 83 KB and the browser performs filtering only.
- The annual chart now describes usable Galactic Centre viewing as the overlap
  of astronomical darkness, acceptable Moon interference and core altitude. It
  no longer presents the result as generic Moon-free time.
- Internal release wording in the public data library was replaced with concise
  visitor-facing download copy.
- Local browser QA confirmed date changes redraw the monthly planner and both
  satellite charts. Site-local wall times remain stable across visitor zones.
- Focused tests passed. Full regression suite: 59 passed. Ruff passed for all
  Stage 4A Python and test files. `git diff --check` passed. Edition validation
  passed.
- Checkpoint tag: `stage-4a-date-driven-instruments`.
- Follow-up UI correction: removed colliding in-chart satellite labels and made
  date controls default to the current observing-site date whenever it falls
  within the page's available edition range. The selectable text key remains.
  Follow-up tag: `stage-4a-current-date-fix`.
- Editorial follow-up: removed the unexplained Moon circles and repetitive
  Milky Way counts from the annual month cards. Cards now prioritise outer-planet
  opposition, favourable meteor showers, then a specific Galactic Centre session.
  Monthly guide introductions use the same event-led recommendation.
  Saturn is correctly promoted in October from the daily solar-elongation data;
  December promotes the Geminids. Public implementation and release commentary
  was replaced with observing guidance.
- Follow-up acceptance command:
  `PYTHONPATH=src .venv/bin/pytest -q tests/test_annual_overview.py tests/test_brand_shell.py tests/test_render_paths.py`.
- Exact resume command:
  `git status --short && PYTHONPATH=src .venv/bin/astro-almanac render --year 2026 --site se_qld --format html`.
- Follow-up verification: the 2026 SE Queensland annual page rendered locally;
  browser inspection confirmed the new month leads and removal of the Moon markers.
  Full regression suite: 60 passed. Ruff and `git diff --check` passed.
- Follow-up tag: `stage-4a-editorial-month-fix`.
- Chips’nCode visual alignment follow-up: restored Atkinson for headings, prose,
  navigation and UI; retained Noto Sans Devanagari for the Sanskrit identity and
  monospace for metadata. Reduced the shared spacing scale, header height, hero
  scale, section padding, card padding and editorial gaps. The compact project
  header now keeps its quiet navigation and active underline through tablet widths.
- Visual alignment acceptance command:
  `PYTHONPATH=src .venv/bin/pytest -q && PYTHONPATH=src .venv/bin/astro-almanac render --year 2026 --site se_qld --format html`.
- Visual alignment verification: annual and monthly pages were inspected at the
  available tablet viewport. The complete four-line identity remains visible,
  navigation stays on one compact row, and the denser hierarchy remains legible.
  Full regression suite: 60 passed; `git diff --check` passed.
- Horizon navigation follow-up: the static page metadata now includes an
  accessible no-JavaScript disclosure linking all three observing horizons.
  Annual, monthly and data pages preserve the visitor's current page type and
  month when switching sites. All three 2026 editions were rerendered locally.
  Focused information-architecture tests and the full 60-test suite pass; Ruff,
  link resolution and `git diff --check` pass. Browser inspection confirmed the
  compact menu and visible current-site state at tablet width.

## Stage 4: Reproducible observing instruments

Implementation order within this single stage:

1. Correct planet and Milky Way observing-window calculations without removing
   existing public CSV fields.
2. Generate stable chart-ready records for Milky Way, planet, Jupiter-moon, and
   Saturn-moon views.
3. Render accessible, horizontally scrollable observing instruments with local
   CSS and progressive JavaScript. Core values remain readable without JavaScript.
4. Add a reusable local annual workflow for every configured observing site.
5. Regenerate a representative edition, inspect it, run focused and full tests,
   then commit and tag the checkpoint.

Affected files:

- `src/paa/compute/milky_way.py`
- `src/paa/compute/planets.py`
- `src/paa/compute/moons.py`
- `src/paa/cli.py`
- `src/paa/validate/reports.py`
- `src/paa/render/almanac_views.py`
- `src/paa/render/html.py`
- `src/paa/render/templates/*.html`
- `src/paa/render/static/styles.css`
- `src/paa/render/static/charts.js`
- `pyproject.toml`
- focused scientific, CLI, renderer, and annual-workflow tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Planet ratings and monthly selections use observable local twilight or night
  samples, never an all-day altitude maximum below a bright Sun.
- Milky Way intervals have exact exclusive end times and never join separate
  nights into one visual line.
- The annual Milky Way view scrolls by date and exposes date, local start and end,
  duration, quality, and peak altitude as text.
- Planet views explain season, local observing period, altitude, rating, and best
  date without depending on colour alone.
- Jupiter and Saturn moon views keep observing dates separate and label local
  time, moon name, and east-west offset.
- A documented `annual-release` command performs all scientific computation on
  the local Mac, validates before rendering, writes provenance and hashes, and
  does not publish automatically or require model tokens.
- Existing commands and existing CSV columns remain compatible. New columns and
  chart-ready files may be additive.
- Keyboard navigation, no-JavaScript use, reduced motion, narrow layouts, and
  light and dark themes remain usable.
- Existing scientific and CLI tests remain green.

Focused test command:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_milky_way.py tests/test_planets.py tests/test_moons.py tests/test_annual_overview.py tests/test_cli.py tests/test_render_paths.py
```

Exact resume command:

```bash
git status --short
sed -n '/## Stage 4:/,/## Stage 3F:/p' docs/IMPLEMENTATION_STATUS.md
PYTHONPATH=src .venv/bin/pytest -q tests/test_milky_way.py tests/test_planets.py tests/test_moons.py tests/test_annual_overview.py tests/test_cli.py tests/test_render_paths.py
```

Results:

- Planet selection now uses the highest target altitude while the Sun is at or
  below -4 degrees. The full-day maximum remains in additive audit columns and
  no longer controls ratings, highlights, or monthly selection.
- Milky Way rows now use an exclusive interval end. Separate nights remain
  separate in both data and presentation.
- The annual page now contains a horizontally scrollable Milky Way night chart,
  twelve compact monthly summaries where data exists, an annual planet matrix,
  and separate Jupiter and Saturn moon-night plots.
- Moon-system samples are centred on a valid planet observing time and locally
  filtered to Sun altitude at or below -4 degrees. Dates are never connected.
- Obsolete PNG production was removed from the active build path. The reviewed
  CSV data drives semantic HTML and CSS instruments directly.
- `astro-almanac annual-release` regenerates selected sites, validates before
  rendering, hashes all edition files, records `published: false`, and performs
  no model calls. The workflow is documented in `docs/ANNUAL_WORKFLOW.md`.
- A 2026 South East Queensland release rehearsal completed successfully with 70
  hashed files. The corrected page was visually inspected in the local browser.
- Focused Stage 4 tests: 21 passed.
- Full regression suite: 56 passed.
- Ruff passed for all changed Python and test files. `git diff --check` passed.
- Checkpoint tag: `stage-4-observing-instruments`.

## Stage 3F: Editorial almanac redesign

Implementation order within this single stage:

1. Shared editorial system, optimised artwork, exact identity, and annual page.
2. Monthly field-guide composition driven entirely by generated data.
3. Grouped data-and-downloads catalogue.
4. Mobile, dark-theme, accessibility, performance, and regression QA.

Affected files:

- `src/paa/render/almanac_views.py`
- `src/paa/render/html.py`
- `src/paa/render/view_models.py`
- `src/paa/render/templates/*.html`
- `src/paa/render/static/styles.css`
- `src/paa/render/static/theme.js`
- `src/paa/render/static/art/*`
- focused renderer and information-architecture tests under `tests/`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- The exact four-line identity is preserved as supplied: `नभस्तल`, `Nabhastala`,
  `त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)`, and
  `One sky at three horizons.`
- Annual, monthly, and data pages share a coherent editorial almanac system while
  retaining page-specific compositions.
- Every displayed date, time, rating, count, recommendation, and chart comes from
  generated output or an explicit unavailable state; prototype sample claims are
  not copied into production templates.
- The annual page provides a concise year overview, the monthly page supports
  field decisions, and the data page provides compact grouped downloads.
- Complete CSV files and existing scientific schemas remain unchanged.
- Artwork is locally bundled, appropriately described or decorative, and reduced
  to a practical static-site payload.
- Keyboard navigation, focus visibility, reduced motion, no-JavaScript operation,
  light and dark themes, narrow layouts, and 200% zoom remain usable.
- Existing scientific and CLI tests remain green.

Focused test command:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_annual_overview.py tests/test_monthly_guide.py tests/test_information_architecture.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py
```

Exact resume command:

```bash
git status --short
sed -n '/## Stage 3F/,/## Stage 3 design checkpoint/p' docs/IMPLEMENTATION_STATUS.md
PYTHONPATH=src .venv/bin/pytest -q tests/test_annual_overview.py tests/test_monthly_guide.py tests/test_information_architecture.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py
```

Results:

- The supplied prototype was used as a visual reference, not as a data source.
  All production summaries remain generated from the existing view models.
- The exact four-line public identity is preserved. The alternative spellings in
  the prototype were not introduced.
- Annual, monthly, and data-library pages now use one editorial almanac system
  with page-specific compositions, locally bundled illustration, and compact
  task-focused information.
- Sixteen light and dark illustrations were resized and converted to WebP. Their
  combined packaged size is about 740 KiB, compared with about 31 MiB for the
  supplied prototype archive.
- Focused Stage 3F tests: 27 passed.
- Full regression suite: 52 passed.
- Ruff and `git diff --check` passed.
- The real 2026 South East Queensland annual, January, and data pages were rendered
  and visually inspected at 1280 px and 390 px widths in light and dark themes.
  No viewport overflow or missing artwork was detected.
- Exact CSV content, scientific calculations, scores, schemas, and CLI signatures
  were not changed.
- Checkpoint tag: `stage-3f-editorial-redesign`.

## Stage 3 design checkpoint

Affected files:

- `.gitignore`
- `docs/STAGE_3_DESIGN_SPEC.md`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks for this checkpoint:

- Supplied 2025 and 2026 almanacs and Joe Cali's location-specific handbook were
  studied across representative annual, monthly, diagram, event, and data pages.
- The user's identity hierarchy and criticism of exhaustive tables are explicit
  design requirements.
- Annual, monthly, landing, and dataset-library responsibilities are specified.
- Complete data remains accessible without occupying the primary reading flow.
- Stage 3 is split into independently committable implementation slices.
- No rendering, styling, CLI, or scientific code changes are included.

## Slice 3A — Contracts and selection helpers

Objective:

- define stable public site/year/month/data paths for all three configured sites;
- add typed annual/monthly presentation contracts;
- add deterministic opportunity eligibility and ranking without changing any
  scientific score.

Affected files:

- `src/paa/paths.py`
- `src/paa/render/view_models.py`
- `tests/test_paths.py`
- `tests/test_view_models.py`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Site IDs map bijectively to `se-qld`, `southern-tasmania`, and `malabar-coast`.
- Annual, monthly, and data-library public paths are POSIX paths and validate years
  and months.
- Failed, incomplete, non-observable, and ordinary poor candidates cannot become
  highlights.
- Eligible candidates sort by rating, score, local date, and stable source order.
- Annual and monthly view-model contracts reject invalid month collections.
- Existing scientific and CLI tests remain green.

Focused test command:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_paths.py tests/test_view_models.py
```

Resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_paths.py tests/test_view_models.py
```

Results:

- Focused tests: 20 passed.
- Full regression suite: 40 passed.
- Ruff passed for all changed Python and test files.
- `git diff --check` passed.
- Scientific calculations, scores, CLI behaviour, templates, and styles were not
  changed.
- Checkpoint tag: `stage-3a-contracts`.

## Slice 3B — Identity and landing page

Objective:

- make the Devanagari name and Sanskrit motto one primary identity block;
- render a no-JavaScript root page for choosing a horizon and available year;
- add a browsable data-library route that links to complete CSV files.

Affected files:

- `src/paa/render/html.py`
- `src/paa/render/templates/_site_header.html`
- `src/paa/render/templates/_site_footer.html`
- `src/paa/render/templates/landing.html`
- `src/paa/render/templates/data_library.html`
- `src/paa/render/static/styles.css`
- `tests/test_brand_shell.py`
- `tests/test_render_paths.py`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- The Sanskrit motto is directly beneath the Devanagari name in markup and layout.
- English identity text is grouped as a visibly subordinate translation.
- The root landing page lists all three locations and links every locally available
  edition without JavaScript.
- Every rendered site/year has a data-library index with record counts and direct
  CSV links; legacy source CSVs are copied into the canonical site tree.
- Annual, monthly, data, and root navigation use valid relative links.
- Existing scientific and CLI tests remain green.

Focused test command:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_brand_shell.py tests/test_render_paths.py
```

Results:

- Focused tests: 8 passed.
- Full regression suite: 42 passed.
- Ruff and `git diff --check` passed.
- The 2026 SE Queensland landing and data-library pages were rendered and visually
  inspected at a narrow browser width in the light theme.
- Scientific calculations, scores, and CLI command signatures were not changed.
- Checkpoint tag: `stage-3b-landing`.

## Slice 3C — Annual overview

Objective:

- replace the exhaustive annual dataset flow with a visual year-at-a-glance;
- select a small, deterministic and category-diverse set of valid opportunities;
- give each month a Moon marker, dark-window summary, lead category, verdict, and
  direct field-guide link;
- place the annual Milky Way chart and planet seasons in decision context.

Affected files:

- `src/paa/render/almanac_views.py`
- `src/paa/render/html.py`
- `src/paa/render/view_models.py`
- `src/paa/render/templates/annual.html`
- `src/paa/render/static/styles.css`
- `tests/test_annual_overview.py`
- `tests/test_brand_shell.py`
- `tests/test_render_paths.py`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- The annual page initially renders no exhaustive data table or dataset sequence.
- Twelve months appear in order with usable empty states and direct links.
- Highlights exclude failed and incomplete rows and preserve category diversity.
- Every “best” statement displays the source value or reason used to justify it.
- Existing Milky Way imagery is contextualised; Jupiter/Saturn strip charts are
  reserved for specialised Stage 4 views.
- Complete CSV access remains prominent through the data library.
- Existing scientific and CLI tests remain green.

Focused test command:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_annual_overview.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py
```

Resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_annual_overview.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py
```

Results:

- Focused tests: 20 passed.
- Full regression suite: 45 passed.
- Ruff passed for all changed Python and test files.
- `git diff --check` passed.
- Real-data render: the 2026 SE Queensland annual edition rendered successfully in
  about 15 seconds.
- Visual QA: the actual annual edition was inspected in-browser at a narrow width;
  its identity hierarchy, calendar grid, ranked events, seasonal context, monthly
  cards, and data-library route render as intended. The generated HTML contains
  each major section exactly once and contains no annual data table.
- Scientific calculations, scores, and CLI command signatures were not changed.
- Checkpoint tag: `stage-3c-annual`.

## Slice 3D — Monthly field guide

Objective:

- replace monthly dataset dumps with a decision-led field-guide composition;
- summarise twilight, lunar conditions, dark windows, Milky Way sessions, planets,
  and trustworthy events from existing values without recalculation;
- link every editorial section to the complete source CSV while keeping core
  information available without JavaScript.

Affected files:

- `src/paa/render/almanac_views.py`
- `src/paa/render/html.py`
- `src/paa/render/view_models.py`
- `src/paa/render/templates/monthly.html`
- `src/paa/render/static/styles.css`
- `tests/test_monthly_guide.py`
- `tests/test_brand_shell.py`
- `tests/test_view_models.py`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Monthly pages contain no generic dataset sequence or exhaustive table initially.
- A visitor can identify representative darkness, Moon conditions, recommended
  sessions, useful planets, and noteworthy events in under a minute.
- Failed and incomplete records appear only as a concise data note, never as a
  recommendation.
- Local dates and times lead; contextual links reach the complete CSV files.
- Narrow layouts preserve document order and horizontal month navigation.
- Existing scientific and CLI tests remain green.

Focused test and resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_monthly_guide.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py
```

Results:

- Focused tests: 20 passed.
- Full regression suite: 47 passed.
- Ruff passed for all changed Python and test files; `git diff --check` passed.
- Real-data render: all twelve 2026 SE Queensland monthly pages and the annual page
  rendered successfully in about 3 seconds.
- Visual QA: January was inspected at a narrow browser width across its title,
  verdict, night-planning, highlight, Milky Way, and planet sections. Document order,
  navigation overflow, local-time emphasis, and contextual downloads render cleanly.
- Planet recommendations require a positive altitude at the source-provided twilight
  time, preventing daytime-only maxima from appearing as field recommendations.
- Annual and monthly pages contain no initial dataset table; full CSV files remain
  linked and unchanged.
- Scientific calculations, scores, schemas, and CLI signatures were not changed.
- Checkpoint tag: `stage-3d-monthly`.

## Slice 3E — Dataset library and visual QA

Objective:

- organise complete CSV downloads by observing purpose and expose concise schema
  details without rendering thousands of rows;
- make provenance and the relationship between editorial views and raw data clear;
- verify keyboard/no-JavaScript behaviour, internal links, theme contrast, reduced
  motion, 200% zoom, and narrow/wide responsive layouts.

Affected files:

- `src/paa/render/html.py`
- `src/paa/render/templates/data_library.html`
- `src/paa/render/static/styles.css`
- `tests/test_information_architecture.py`
- `tests/test_brand_shell.py`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Complete CSVs, including failed/unavailable rows, remain byte-for-byte available.
- Datasets are grouped and each card names its file, record count, columns, and
  intended use without requiring JavaScript.
- Every local HTML link and referenced asset resolves in a three-site fixture build.
- Annual and monthly core information remains usable with scripts disabled.
- Keyboard focus, reduced motion, dark/light themes, narrow/wide layout, and 200%
  zoom receive focused static and visual checks.
- Existing scientific and CLI tests remain green.

Focused test and resume command:

```bash
git status --short
PYTHONPATH=src .venv/bin/pytest -q tests/test_information_architecture.py tests/test_brand_shell.py tests/test_render_paths.py
```

Results:

- Focused tests: 14 passed.
- Full regression suite: 52 passed.
- Ruff passed for every file changed in this slice; `node --check` and
  `git diff --check` passed.
- Repository-wide Ruff still reports 48 pre-existing findings in unrelated API,
  compute, I/O, source, and legacy test files; this slice does not modify them.
- Link QA: every local page, asset, CSV link, and fragment resolves across fixture
  editions for all three configured sites; IDs are unique and editions do not
  cross-link.
- Visual QA: the real 2026 data library was inspected at the available tablet-width
  viewport in light and dark themes. Group navigation, two-column cards, contrast,
  and an expanded native details disclosure render cleanly.
- Accessibility changes: the light accent now exceeds 4.5:1 against paper, all
  normal text tokens in both themes have regression tests, and the body-wide 20rem
  minimum was removed to prevent forced horizontal scrolling under text zoom.
- No-JavaScript and 200% reflow received static contract checks. The preview surface
  blocks programmatic browser zoom, so a manual 200% visual confirmation remains
  before the final Stage 3 completion tag.
- Complete CSV files, including failed rows, remain unchanged and directly linked.
- Scientific calculations, scores, schemas, and CLI signatures were not changed.
- Checkpoint tag: `stage-3e-qa-ready`.

## Verification

- Focused test command: `PYTHONPATH=src .venv/bin/pytest -q tests/test_render_paths.py tests/test_brand_shell.py`
- Focused result: 6 passed.
- Full test command: `PYTHONPATH=src .venv/bin/pytest -q`
- Full result: 31 passed.
- Static checks: Ruff passed for the renderer and renderer tests; `node --check`
  passed for `theme.js`; `git diff --check` passed.
- Package check: a wheel built successfully and contained all templates, CSS,
  JavaScript, bundled font subsets, and font licence files.
- Render smoke test: the existing 2026 `se_qld` material rendered successfully to
  `output/se_qld/2026/` through the legacy read fallback.
- Visual smoke test: annual and January monthly pages were inspected in a browser
  in light and dark themes. The identity fonts, hierarchy, navigation, tables, and
  horizontal overflow treatments rendered correctly at the tested desktop width.
- Note: this machine's pre-existing editable virtualenv intermittently omits the
  project `.pth` after a Homebrew Python patch upgrade. Prefix local commands with
  `PYTHONPATH=src` until the virtualenv is recreated; the built wheel is complete.
- Stage 3 design checkpoint: documentation-only; `git diff --check` passed. No code
  tests were required for the reference study.
- Stage 3A focused test command:
  `PYTHONPATH=src .venv/bin/pytest -q tests/test_paths.py tests/test_view_models.py`
- Stage 3A focused result: 20 passed.
- Stage 3A full result: 40 passed.
- Stage 3B focused test command:
  `PYTHONPATH=src .venv/bin/pytest -q tests/test_brand_shell.py tests/test_render_paths.py`
- Stage 3B focused result: 8 passed.
- Stage 3B full result: 42 passed.
- Stage 3C focused test command:
  `PYTHONPATH=src .venv/bin/pytest -q tests/test_annual_overview.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py`
- Stage 3C focused result: 20 passed.
- Stage 3C full result: 45 passed.
- Stage 3D focused test command:
  `PYTHONPATH=src .venv/bin/pytest -q tests/test_monthly_guide.py tests/test_brand_shell.py tests/test_render_paths.py tests/test_view_models.py`
- Stage 3D focused result: 20 passed.
- Stage 3D full result: 47 passed.
- Stage 3E focused test command:
  `PYTHONPATH=src .venv/bin/pytest -q tests/test_information_architecture.py tests/test_brand_shell.py tests/test_render_paths.py`
- Stage 3E focused result: 14 passed.
- Stage 3E full result: 52 passed.

## Resume

From the repository root, run:

```bash
git status --short
git log -1 --oneline
git describe --tags --exact-match
PYTHONPATH=src .venv/bin/pytest -q
```

Stage 2 remains complete at tag `stage-2-brand-shell`. Stage 3A is complete at tag
`stage-3a-contracts`, Stage 3B at tag `stage-3b-landing`, and Stage 3C at tag
`stage-3c-annual`. Stage 3D is complete at tag `stage-3d-monthly`. Do not begin
Stage 4. Stage 3E code is checkpointed at `stage-3e-qa-ready`; confirm the annual,
monthly, and data-library pages at 200% browser zoom before applying the final
`stage-3-information-architecture` tag.

## External setup

- Intended GitHub repository: `Marzogh/nabhastala`
- Intended Pages URL: `https://marzogh.github.io/nabhastala/`
- GitHub CLI and SSH authentication both succeed for `Marzogh`.
- Public repository created: `https://github.com/Marzogh/nabhastala`
- `origin` uses SSH and `main` tracks `origin/main`.
