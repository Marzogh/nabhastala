# Nabhastala implementation status

This file is the restart point for the staged redesign. Do not begin a new stage
until the previous stage is committed, tagged, and marked complete here.

## Current stage

- Stage: 0 — Repository safety and baseline
- State: complete
- Objective: establish recoverable version history without changing computational behaviour
- Started: 2026-09-14

## Stage 0 work

Affected files:

- `.gitignore`
- `LICENSE`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION_STATUS.md`

Acceptance checks:

- Git repository uses the `main` branch.
- Generated output, caches, build products, and local databases are ignored.
- Existing tests pass before renderer changes begin.
- Baseline is committed and tagged `stage-0-baseline`.
- No computation or rendering implementation is changed.

## Verification

- Baseline test command: `.venv/bin/python -m pytest`
- Result: 13 passed in 4.18 seconds on Python 3.14.6

## Resume

From the repository root, run:

```bash
git status --short
git log -1 --oneline
.venv/bin/python -m pytest
```

Stage 0 is complete. After the checkpoint commit is present and the working tree
is clean, the next authorized work is Stage 1: rendering contract and multi-site
paths.

## External setup

- Intended GitHub repository: `Marzogh/nabhastala`
- Intended Pages URL: `https://marzogh.github.io/nabhastala/`
- GitHub CLI authentication for `Marzogh` was invalid when planning began.
- Remote creation and push remain pending until authentication is restored.
