# Part 1 Validation Report

## Result

All Phase 0-7 completion gates pass for the current Part 1 run. The authoritative
machine-readable audit is `outputs/phase_validation.json`.

Run the audit with:

```bash
uv run --no-sync part1-validate-phases
```

## Locked Protocol

- Use official parent-company identity, mission, purpose, values, About Us, or equivalent
  overview pages.
- Select the replayable target-year capture nearest June 30 at 12:00 UTC.
- Do not substitute adjacent-year captures.
- Preserve every company-year as an explicit status row.
- Treat empty text, error-like pages, failed replay retrievals, low-alpha extraction, and
  extremely thin text as non-usable. Short-but-substantive text remains usable and is
  marked for review through QA flags rather than discarded.
- Compare only adjacent calendar years.
- Require evidence for deterministic theme classifications.

## Phase Status

| Phase | Current research gate | Evidence |
|---|---|---|
| 0. Environment and contract | Pass | 450 targets; 50 companies; 2016-2024; five balanced sectors |
| 1. Pilot and rule lock | Pass | Locked protocol above and `docs/methodology.md` |
| 2. Candidate registry | Pass | Every required company has a reviewed candidate entry |
| 3. CDX collection and selection | Pass | 450 status rows; zero `discovery_incomplete` rows |
| 4. Text extraction | Pass | Selected captures have artifacts; 450 extraction/gap decisions |
| 5. Change detection | Pass | `change_events.csv` has one row per company-year |
| 6. Theme, linguistic, and LLM analysis | Pass | Theme observations, taxonomy, linguistic metrics, and local LLM outputs |
| 7. Reporting and deliverables | Pass | Final dataset, summary, coverage, and audits |

## Extraction and Gap Evidence

- Completed extraction/gap review decisions: 450.
- Usable records: 358 of 450.

Status breakdown:

- `insufficient_substantive_text`: 12
- `no_cdx_capture`: 60
- `no_eligible_capture`: 5
- `retrieval_failed`: 15
- `usable`: 358

Usable records retain source URL, Wayback URL, capture timestamp, raw SHA-256,
clean-text SHA-256, extraction quality, theme evidence, and linguistic metrics.
Non-usable records are kept in the panel as explicit gaps and excluded from
substantive values interpretation.

## Change Validation

Adjacent-year change detection is complete for all 450 company-year rows.
The pipeline compares only adjacent calendar years within the same ticker. It never
substitutes neighboring years for missing target-year captures, and gap rows are not
interpreted as evidence of stability or change.

## Theme Analysis

Row-level structured coding uses the committed deterministic baseline. A separate local LLM layer
was also run with cached `Qwen/Qwen3-1.7B` on Apple MPS:

- Snapshot LLM annotations completed: 358 usable rows.
- Snapshot skipped rows: 92 non-usable rows.
- Adjacent-year LLM change annotations completed: 299 usable current/prior pairs.
- Change skipped rows: 50 no-prior rows and 101 non-usable current/prior pairs.
- Snapshot quality flags: 358 `candidate_interpretive_signal`, 92 `not_applicable`.
- Change quality flags: 137 `candidate_interpretive_signal`, 162 `medium_unstructured`, 151
  `not_applicable`.
- Output manifest: `outputs/llm_analysis/llm_analysis_summary.json`.

The local LLM outputs retain prompt hashes, response hashes, input text hashes, package versions,
model family, device metadata, and quality flags. They are treated as audit triage and triangulation
rather than as replacements for the deterministic theme and change fields.

## Automated Verification

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync ruff check part1_stated_values/src part1_stated_values/tests
uv run --no-sync part1-run
uv run --no-sync part1-llm-analysis
uv run --no-sync part1-validate-phases
```

The structural requirement audit is stored at `outputs/requirement_audit.json`.

## Boundaries

The current deliverable does not impute missing values. Company-years without usable
archived text remain in the 450-row panel with explicit status and gap reasons.
