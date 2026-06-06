# Part 1 Validation Report

## Result

All Phase 0-7 completion gates pass for the current Part 1 run. The authoritative
machine-readable audit is `outputs/phase_validation.json`.

Run the audit with:

```bash
uv run --no-sync part1-validate-phases
```

## Phase Status

| Phase | Implementation and tests | Current research gate | Evidence |
|---|---|---|---|
| 0. Environment and contract | Complete | Pass | 450 company-year targets, 50 companies, 2016-2024, five sectors with 10 companies each |
| 1. Difficult pilot and rule lock | Complete | Pass | `docs/pilot_decision_record.md` and `docs/pilot_approval.md` |
| 2. Candidate registry | Complete | Pass | Every required company has a reviewed candidate entry |
| 3. CDX collection and selection | Complete | Pass | `acquisition_status.csv` has 450 rows and zero `discovery_incomplete` rows |
| 4. Text extraction | Complete | Pass | 248 selected captures, 248 text artifacts, 450 completed review decisions, zero unresolved queue rows |
| 5. Change detection | Complete | Pass | `change_events.csv` has one row per company-year and `docs/change_validation.md` records the rule audit |
| 6. Theme and LLM analysis | Complete | Pass | `theme_observations.csv`, `docs/taxonomy.md`, and `docs/llm_analysis.md` |
| 7. Reporting and deliverables | Complete | Pass | 450-row final dataset, summary, coverage, requirement audit, and phase audit |

## Automated Verification

The test suite contains phase-specific tests for target contracts, candidate registry validation,
CDX discovery, annual selection, retrieval, extraction, adjacent-year comparison, taxonomy,
reporting, final output audits, and phase gates.

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync part1-process
uv run --no-sync part1-validate-phases
```

The structural requirement audit is stored at `outputs/requirement_audit.json`.

## Review Evidence

- `data/review/review_decisions.csv` contains one completed extraction/gap adjudication decision
  per final company-year row.
- `data/review/manual_review_queue.csv` is empty because all current review items are resolved by
  the deterministic protocol.
- `docs/extraction_validation.md` records extraction and gap handling.
- `docs/change_validation.md` records adjacent-year change validation.
- `docs/llm_analysis.md` records the reproducible theme and linguistic analysis choice.

## Boundaries

The current deliverable does not impute missing values. Company-years without usable archived text
remain in the 450-row panel with explicit status and gap reasons. Row-level theme coding uses the
committed deterministic baseline rather than an external, non-replayable LLM call; the external LLM
path remains available as a later robustness extension.
