# Nabhastala implementation status

This file is the restart point for the staged redesign. Do not begin a new stage
until the previous stage is committed, tagged, and marked complete here.

## Current stage

- Stage: 3 — User-friendly information architecture
- State: slice 3E implementation complete; manual 200% zoom confirmation pending
- Objective: replace the dataset-led reading experience with a visual annual
  overview and decision-led monthly field guides
- Design specification: `docs/STAGE_3_DESIGN_SPEC.md`
- Study date: 2026-09-14

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
