# Part 1: Stated Values

This directory contains the reproducible pipeline for collecting and analyzing archived corporate “About Us,” mission, purpose, and values pages from the Wayback Machine.

## Current Status

The end-to-end pipeline is implemented and tested. The latest live run is structurally complete,
but Wayback CDX availability and the absence of external LLM credentials prevent the current run
from satisfying every research completion gate. Human approval and validation gates also remain
open by design. See `docs/validation_report.md` and `outputs/phase_validation.json`.

Implemented stages:

- canonical 50-company manifest and 450-row target grid
- reviewed candidate-page registry
- resumable CDX discovery and deterministic annual snapshot selection
- replay retrieval, visible-text extraction, and QA flags
- adjacent-year change detection
- evidence-backed theme and linguistic baseline
- final company-year dataset, supporting outputs, review queue, and phase/requirement audits

## Layout

Part 1 is self-contained under this directory. The main Python package lives at
`part1_stated_values/src/org_auth_part1/`; tests live at `part1_stated_values/tests/`.
The repository-level `pyproject.toml` exposes the package through `uv` command-line scripts.

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

Run the end-to-end workflow:

```bash
uv run --no-sync part1-validate-registry
uv run --no-sync part1-discover
uv run --no-sync part1-select
uv run --no-sync part1-process
uv run --no-sync part1-validate-phases
```

All discovery and replay stages are resumable. Rerun them when Wayback is available; successful
cached results are reused.

For Phase 3 recovery, prefer ticker-sized batches so Wayback timeouts do not invalidate unrelated
company-years:

```bash
uv run --no-sync part1-discover --ticker AAPL --retries 5 --timeout-seconds 120
uv run --no-sync part1-select
uv run --no-sync part1-process
uv run --no-sync part1-validate-phases
```

CDX discovery is cached at the `candidate URL × year` level and logged in
`data/processed/cdx_query_log.csv`.

## Phase Tests

Part 1 has eight phases, numbered Phase 0 through Phase 7. Unit tests verify the code within each
phase; `part1-validate-phases` separately evaluates whether the research completion gates are met.

| Phase | Test files |
|---|---|
| Phase 0 | `test_targets.py`, `test_registry.py` |
| Phase 1 | `test_registry.py`, methodology and review protocol |
| Phase 2–3 | `test_discover.py`, `test_acquire.py`, `test_select.py` |
| Phase 4 | `test_extract.py`, `test_pipeline.py` |
| Phase 5 | `test_compare.py` |
| Phase 6 | `test_analyze.py` |
| Phase 7 | `test_report.py`, `test_validate.py`, `test_phase_validation.py` |

Run all phase tests:

```bash
uv run --no-sync pytest
uv run --no-sync ruff check .
```

## Key Outputs

- `outputs/part1_company_year.csv`: required 450-row final dataset
- `outputs/change_events.csv`: adjacent-year change results
- `outputs/theme_observations.csv`: long-format evidence-backed themes
- `outputs/coverage_report.json`: coverage and failure status summary
- `outputs/requirement_audit.json`: structural instruction audit
- `outputs/phase_validation.json`: phase-by-phase completion gates
- `data/review/manual_review_queue.csv`: records requiring user review
- `docs/summary.md`: concise written summary

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

## Current Run Limitations

- Wayback CDX returned widespread `503 Service Unavailable` and connection errors during the live
  run. These are preserved as `discovery_incomplete`, not misreported as missing captures.
- No external LLM credentials were available. The committed theme analysis is a deterministic,
  evidence-backed baseline; the phase audit correctly leaves the LLM completion gate open.
- Pilot approval, extraction review, and change-classification validation require a human reviewer.
  The phase audit intentionally leaves these gates open until signed review records exist.
