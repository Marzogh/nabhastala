-- Baseline schema bootstrap for personal-astro-almanac.
-- Canonical migrations are currently code-first in src/paa/io/postgres.py.
-- This file exists for milestone 10 tracking and external DB bootstrap workflows.

CREATE SCHEMA IF NOT EXISTS paa;
CREATE TABLE IF NOT EXISTS paa.runs (
  run_id BIGSERIAL PRIMARY KEY,
  year INTEGER NOT NULL,
  site_id TEXT NOT NULL,
  built_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (year, site_id)
);
