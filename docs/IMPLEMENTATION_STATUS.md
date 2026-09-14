# Nabhastala implementation status

This file is the restart point for the staged redesign. Do not begin a new stage
until the previous stage is committed, tagged, and marked complete here.

## Current stage

- Stage: 1 — Rendering contract and multi-site paths
- State: complete
- Objective: isolate every site/year build while retaining read-only access to legacy outputs
- Started: 2026-09-14

## Stage 1 work

Expected areas:

- output-path helpers and CLI consumers
- HTML, validation, provenance, and occultation path consumers
- renderer view-model helpers
- deterministic renderer fixture and focused tests
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- New writes use `output/<site>/<year>/`.
- Legacy `output/<year>/` content remains readable and is never written.
- Existing CLI commands remain valid.
- Human labels, local datetimes, ratings, missing values, and escaping are tested.
- Full regression suite passes.
- Work is committed and tagged `stage-1-multisite-contract`.

## Verification

- Focused test command: `.venv/bin/python -m pytest tests/test_paths.py tests/test_view_models.py tests/test_render_paths.py`
- Full test command: `.venv/bin/python -m pytest`
- Result: 16 focused tests passed; 27 full-suite tests passed on Python 3.14.7
- Lint: import and error checks passed for all Stage 1 files
- Smoke test: legacy 2026 `se_qld` data rendered to
  `output/se_qld/2026/almanac.html` with 12 monthly pages
- Safety: legacy fallback now requires a matching run-manifest `site_id`

## Resume

From the repository root, run:

```bash
git status --short
git log -1 --oneline
.venv/bin/python -m pytest
```

Stage 1 is complete. After the checkpoint commit is present and the working tree
is clean, the next authorized work is Stage 2: Nabhastala brand foundation.

## External setup

- Intended GitHub repository: `Marzogh/nabhastala`
- Intended Pages URL: `https://marzogh.github.io/nabhastala/`
- GitHub CLI and SSH authentication both succeed for `Marzogh`.
- Public repository created: `https://github.com/Marzogh/nabhastala`
- `origin` uses SSH and `main` tracks `origin/main`.
