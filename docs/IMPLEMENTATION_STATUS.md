# Nabhastala implementation status

This file is the restart point for the staged redesign. Do not begin a new stage
until the previous stage is committed, tagged, and marked complete here.

## Current stage

- Stage: 2 — Nabhastala brand foundation
- State: complete
- Objective: replace string-built documents with a reusable, accessible Nabhastala page shell
- Started: 2026-09-14

## Stage 2 work

Expected areas:

- packaged Jinja templates and reusable renderer view models
- shared CSS tokens, local font assets, and minimal theme script
- annual and monthly semantic page shells
- renderer, packaging, accessibility, and visual smoke tests
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Exact supplied identity appears on annual and monthly pages.
- Templates and assets work from an installed package and direct file URLs.
- Light, dark, focus, reduced-motion, narrow-screen, and print treatments exist.
- Core content and navigation work without JavaScript.
- Full regression suite passes.
- Work is committed and tagged `stage-2-brand-shell`.

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

## Resume

From the repository root, run:

```bash
git status --short
git log -1 --oneline
git describe --tags --exact-match
PYTHONPATH=src .venv/bin/pytest -q
```

Stage 2 is complete. Do not begin Stage 3 until the user authorizes it.

## External setup

- Intended GitHub repository: `Marzogh/nabhastala`
- Intended Pages URL: `https://marzogh.github.io/nabhastala/`
- GitHub CLI and SSH authentication both succeed for `Marzogh`.
- Public repository created: `https://github.com/Marzogh/nabhastala`
- `origin` uses SSH and `main` tracks `origin/main`.
