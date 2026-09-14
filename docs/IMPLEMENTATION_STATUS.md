# Nabhastala implementation status

This file is the restart point for the staged redesign. Do not begin a new stage
until the previous stage is committed, tagged, and marked complete here.

## Current stage

- Stage: 3 — User-friendly information architecture
- State: slice 3A complete
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

## Resume

From the repository root, run:

```bash
git status --short
git log -1 --oneline
git describe --tags --exact-match
PYTHONPATH=src .venv/bin/pytest -q
```

Stage 2 remains complete at tag `stage-2-brand-shell`. Stage 3A is complete at tag
`stage-3a-contracts`. Do not begin slice 3B until the user authorizes it.

## External setup

- Intended GitHub repository: `Marzogh/nabhastala`
- Intended Pages URL: `https://marzogh.github.io/nabhastala/`
- GitHub CLI and SSH authentication both succeed for `Marzogh`.
- Public repository created: `https://github.com/Marzogh/nabhastala`
- `origin` uses SSH and `main` tracks `origin/main`.
