# Part 1: Stated Values

This directory contains the reproducible pipeline for collecting and analyzing archived corporate “About Us,” mission, purpose, and values pages from the Wayback Machine.

## Current Status

Phase 0 foundations are implemented:

- canonical 50-company manifest
- deterministic 450-row company-year target grid
- typed data contracts
- Wayback CDX query and response parsing
- deterministic annual snapshot ranking around June 30
- offline unit tests

The next milestone is a difficult cross-sector pilot. Page candidates and methodological thresholds will be reviewed before full collection.

## Setup

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync ruff check .
```

VS Code can use the project interpreter at `.venv/bin/python`.
Rerun `uv sync --no-editable` after changing package source files.

## Commands

Build the 450-row target grid:

```bash
uv run --no-sync part1-build-targets
```

Query CDX for a reviewed candidate URL:

```bash
uv run --no-sync part1-query-cdx \
  --ticker MSFT \
  --url https://www.microsoft.com/en-us/about \
  --output part1_stated_values/data/interim/msft_cdx.json
```

## Snapshot Selection Rule

For each target year, the pipeline ranks eligible captures by:

1. validity and page eligibility
2. absolute distance from June 30 at 12:00 UTC
3. capture timestamp as a deterministic tie-breaker

Adjacent-year captures are never substituted for a missing target year.

## Data Policy

- `config/companies.csv` is the authoritative required sample.
- `data/processed/target_company_years.csv` contains all 450 target keys.
- Raw HTML and local intermediate artifacts are ignored by Git.
- Every final usable record must retain source and selection provenance.
