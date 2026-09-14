#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

if command -v docker >/dev/null 2>&1; then
  docker compose up -d postgres || true
  export PAA_DATABASE_URL="postgresql://postgres:postgres@localhost:55432/astro"
fi

astro-almanac db-init --database-url "${PAA_DATABASE_URL:-}"
