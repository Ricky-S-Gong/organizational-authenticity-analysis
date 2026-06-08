# Part 1: Stated Values

Part 1 collects and analyzes archived corporate stated-values pages for the fixed 50-company
sample and 2016-2024 company-year window used throughout the assessment.

## What I Did

I built a reproducible Wayback Machine pipeline that starts from a reviewed company and page
registry, queries official Wayback CDX endpoints, selects one annual corporate identity/value page
snapshot per company-year when available, extracts substantive visible text, and generates change,
theme, linguistic, coverage, and validation outputs.

The current run preserves all 450 required company-year rows. It produces 358 usable analytical
records, covering 79.6% of the target panel. The remaining 92 rows are retained as documented gaps
rather than imputed or interpreted as absence of stated values.

## Why This Design

The assignment asks for archived corporate "About Us" or equivalent mission/values pages. Those
pages are historically unstable: URLs move, redirects change, and some snapshots are JavaScript
shells, error pages, or narrow subpages. The pipeline therefore separates the problem into auditable
stages:

- define eligible official page families before collection;
- query Wayback by candidate URL and target year;
- choose the same-year capture closest to June 30 at 12:00 UTC;
- keep every target company-year as an explicit status row;
- analyze only cleaned substantive text, while retaining source and extraction provenance.

This design favors traceability over silent coverage inflation. Adjacent-year captures are never
substituted for missing target-year snapshots.

## Assumptions

- The supplied 50-company list is the authoritative sample.
- A corporate mission, purpose, values, "Who We Are," "About Us," or equivalent corporate overview
  page is a valid stated-values source when it represents the parent company rather than a product,
  subsidiary, newsroom, campaign, careers, investor, or third-party page.
- June 30 at 12:00 UTC is a reasonable annual anchor for deterministic snapshot selection.
- A same-year target can be non-usable because of CDX gaps, replay failures, error pages, or
  insufficient substantive text; those cases should remain explicit missingness, not zeros.
- Deterministic keyword/theme coding is an auditable baseline. LLM-assisted classification would
  require recorded model, prompt, parameters, input hashes, output schema, and validation evidence.

## Current Completion Status

Part 1 now passes the strict Phase 0-7 completion gate used in this repository. The authoritative
machine-readable check is `outputs/phase_validation.json`.

Current phase status:

- Phase 0 environment and target contract: pass.
- Phase 1 pilot/rule lock: pass.
- Phase 2 candidate registry: pass.
- Phase 3 CDX collection and snapshot selection: pass; zero company-years remain
  `discovery_incomplete`.
- Phase 4 text extraction: pass.
- Phase 5 change detection: pass.
- Phase 6 theme, linguistic, and LLM analysis: pass. The deterministic baseline is the primary
  structured output; local open-source LLM annotations are retained as an auditable exploratory
  layer.
- Phase 7 reporting and deliverables: pass.

Current final-output coverage:

- `usable`: 358 of 450 company-years.
- `no_cdx_capture`: 60.
- `retrieval_failed`: 15.
- `insufficient_substantive_text`: 12.
- `no_eligible_capture`: 5.

## LLM Requirement Map

The assignment asks for an LLM-based pipeline that analyzes each snapshot for three items. The
submitted Part 1 outputs satisfy that requirement through a reproducible deterministic baseline plus
a logged local Qwen LLM audit layer:

| Instruction item | Where to review it |
|---|---|
| (a) Whether the page changed from the prior year | Main structured fields: `outputs/part1_company_year.csv` columns `changed_from_prior`, `change_score`, and `change_magnitude`; detailed adjacent-year evidence: `outputs/change_events.csv`; LLM change notes: `outputs/llm_analysis/llm_change_analysis.csv` |
| (b) What value/thematic categories are present | Main structured fields: `outputs/part1_company_year.csv` column `theme_categories`; evidence table: `outputs/theme_observations.csv`; category definitions and academic basis: `docs/taxonomy.md`; LLM snapshot notes: `outputs/llm_analysis/llm_snapshot_analysis.csv` |
| (c) Any notable linguistic shifts over time | Main structured fields: `outputs/part1_company_year.csv` columns `linguistic_metrics` and `linguistic_shift_notes`; adjacent-year evidence: `outputs/change_events.csv`; LLM change notes: `outputs/llm_analysis/llm_change_analysis.csv` |

The LLM run metadata, model choice, prompt/version information, package versions, hashes, device,
and coverage counts are recorded in `outputs/llm_analysis/llm_analysis_summary.json`.

## Known Limitations

- The assessment does not require 100% scraping coverage, but 92 company-years remain non-usable
  and are documented as explicit gaps.
- The hardest remaining gaps are confirmed no-CDX years, no-eligible-capture years, replay
  failures, and thin/error-like archived pages, not ordinary parsing failures.
- Some companies changed page architecture over time; generated historical URL candidates reduce
  this problem but do not eliminate it.
- The deterministic taxonomy is transparent and reproducible, but it can miss synonyms, context,
  and subtle shifts in values language.
- The local LLM layer uses cached `Qwen/Qwen3-1.7B` on Apple MPS. It is stronger than the
  earlier FLAN-small baseline while still fitting the 16 GB M1 Pro environment; LLM notes remain
  audit triage and triangulation rather than standalone evidence.
- Theme and change outputs are strongest for usable rows; non-usable rows should be treated as
  documented missing observations.

## What I Would Do Differently With More Time

- Add more company-specific historical URL research for the remaining `no_cdx_capture` rows.
- Run a larger manual validation sample comparing selected pages against archived homepages and
  company-site navigation.
- Re-run selected LLM samples with a larger quantized Qwen model if stronger external compute is
  available, while keeping the deterministic baseline as the auditable primary output.
- Expand replay recovery for JavaScript-heavy archived pages and preserve screenshots or rendered
  text where allowed by the reproducibility constraints.

## Deliverables

- [`docs/summary.md`](docs/summary.md): concise summary of coverage, method, interpretation, and
  limitations.
- [`docs/methodology.md`](docs/methodology.md): page-selection rules, Wayback workflow, extraction
  method, pipeline evolution, validation design, and Mermaid workflow diagram.
- [`docs/validation_report.md`](docs/validation_report.md): phase status, extraction/gap evidence,
  and verification commands.
- [`docs/codebook.md`](docs/codebook.md): column definitions for the final company-year dataset.
- [`docs/taxonomy.md`](docs/taxonomy.md): deterministic stated-values theme taxonomy.
- [`outputs/part1_company_year.csv`](outputs/part1_company_year.csv): required 450-row final
  company-year panel.
- [`outputs/change_events.csv`](outputs/change_events.csv): adjacent-year change classifications
  and evidence.
- [`outputs/theme_observations.csv`](outputs/theme_observations.csv): long-format theme evidence.
- [`outputs/llm_analysis/llm_snapshot_analysis.csv`](outputs/llm_analysis/llm_snapshot_analysis.csv):
  local LLM notes for usable snapshots plus explicit skipped rows for non-usable observations.
- [`outputs/llm_analysis/llm_change_analysis.csv`](outputs/llm_analysis/llm_change_analysis.csv):
  local LLM notes for adjacent usable company-year pairs.
- [`outputs/llm_analysis/llm_analysis_summary.json`](outputs/llm_analysis/llm_analysis_summary.json):
  model, prompt, package-version, hash, and quality-flag manifest.
- [`outputs/coverage_report.json`](outputs/coverage_report.json): status counts and coverage rate.
- [`outputs/requirement_audit.json`](outputs/requirement_audit.json): structural audit against the
  required output contract.
- [`outputs/phase_validation.json`](outputs/phase_validation.json): phase-by-phase completion
  gates.
- [`data/processed/acquisition_status.csv`](data/processed/acquisition_status.csv): company-year
  acquisition status and selected snapshot provenance.
- [`data/processed/annual_snapshot_candidates.csv`](data/processed/annual_snapshot_candidates.csv):
  ranked same-year Wayback candidates and rejection reasons.
- [`data/processed/cdx_query_log.csv`](data/processed/cdx_query_log.csv): CDX query strategy,
  attempts, capture counts, and cache paths.
- [`data/review/review_decisions.csv`](data/review/review_decisions.csv): completed extraction and
  gap adjudication decisions.

## Commands

The commands below reproduce the Part 1 workflow from the repository root.

Install the shared root `uv` environment:

```bash
uv sync
```

Run the full pipeline over all configured companies:

```bash
uv run --no-sync part1-run
```

Run the full pipeline as a longer scraping job with explicit progress logs:

```bash
nohup uv run --no-sync part1-run \
  --discovery-retries 8 \
  --timeout-seconds 180 \
  --replay-retries 5 \
  --workers 4 \
  --progress-log part1_stated_values/data/interim/part1_run_progress.jsonl \
  --state-file part1_stated_values/data/interim/part1_run_state.json \
  > part1_stated_values/outputs/part1_run.log 2>&1 &
```

Monitor a long run from another terminal:

```bash
uv run --no-sync part1-run-status
```

Run an incremental improvement pass only for currently non-usable rows:

```bash
uv run --no-sync part1-run \
  --only-nonusable \
  --discovery-retries 8 \
  --timeout-seconds 180 \
  --replay-retries 2 \
  --workers 1 \
  --fetch-timeout-seconds 120 \
  --fetch-retries 12
```

`--only-nonusable` reads `outputs/part1_company_year.csv`, limits network-heavy work to rows whose
current `observation_status` is not `usable`, preserves prior usable artifacts, and regenerates the
450-row final dataset plus downstream audits.

Validate the current phase gates:

```bash
uv run --no-sync part1-validate-phases
```

Run the local open-source LLM analysis layer:

```bash
uv run --no-sync part1-llm-analysis
```

The command uses cached `Qwen/Qwen3-1.7B` by default with `local_files_only=true`. On a machine
without the cached model, run the same command once with `--allow-model-download`. It records prompt
hashes, response hashes, input text hashes, package versions, model family, device, and quality flags
in `outputs/llm_analysis/`.

Run tests and lint:

```bash
uv run --no-sync pytest
uv run --no-sync ruff check part1_stated_values/src part1_stated_values/tests
uv run --no-sync ruff format --check part1_stated_values/src part1_stated_values/tests
```

Advanced stage-level commands remain available for debugging:

```bash
uv run --no-sync part1-discover
uv run --no-sync part1-select
uv run --no-sync part1-process
```

## Data Policy

Only auditable deliverables and reproducible project files should be committed. Raw replayed HTML,
year-level CDX cache JSON, local progress logs, Python bytecode, local virtual environments, and
scratch files are runtime artifacts and can be regenerated by rerunning the commands above.

Every usable final row retains source URL, Wayback URL, capture timestamp, raw-content hash,
clean-text hash, extraction quality, theme evidence, and linguistic metrics. Every non-usable row
retains an explicit `observation_status` and `gap_reason`.
