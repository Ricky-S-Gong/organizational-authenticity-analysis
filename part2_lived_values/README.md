# Part 2: Lived Values

Part 2 collects and analyzes one auditable disclosure type for the same 50 companies and
2016-2024 window used in Part 1.

## Design Choice

This pipeline uses SEC EDGAR `DEF 14A` proxy statements as the lived-values disclosure source.
Proxy statements are not direct observations of behavior, but they are official, free,
consistently archived, and highly reproducible. This makes them a stronger fit for an audited
proof-of-concept than manually collected ESG or sustainability PDFs.

## Folder Contract

All Part 2 work lives under this directory:

- `src/org_auth_part2/`: reusable collection, extraction, analysis, logging, and validation code.
- `tests/`: Part 2 tests only.
- `config/`: company-year target grid generated from the Part 1 company manifest.
- `data/interim/`: SEC ticker/CIK and submissions API caches plus progress/state logs.
- `data/raw/filings/`: downloaded SEC primary filing documents.
- `data/processed/`: extracted text, filing metadata, and review queues.
- `outputs/`: final dataset, coverage report, requirement audit, and run logs.
- `outputs/part2_company_year_compact.csv`: git-friendly company-year dataset without the full
  extracted text column.
- `outputs/part2_company_year.csv`: full local dataset with extracted text. This is intentionally
  ignored by Git because it is large and reproducible from SEC sources.
- `docs/`: methodology, codebook, audit notes, and summary.

## Deliverables

- [`docs/summary.md`](docs/summary.md): concise summary of the Part 2 dataset, coverage, and main
  findings.
- [`docs/methodology.md`](docs/methodology.md): source choice, SEC filing selection rule,
  extraction method, modeling choices, and construct-validity caveats.
- [`docs/text_mining_analysis.md`](docs/text_mining_analysis.md): main analysis report with
  figures, Markdown tables, deterministic text mining, and enhanced model-based checks.
- [`docs/codebook.md`](docs/codebook.md): column definitions for the final company-year dataset.
- [`docs/top_shift_excerpt_audit.md`](docs/top_shift_excerpt_audit.md): qualitative audit of
  selected large theme shifts.
- [`outputs/part2_company_year_compact.csv`](outputs/part2_company_year_compact.csv): git-friendly
  company-year dataset without the full extracted text column.
- [`outputs/coverage_report.json`](outputs/coverage_report.json): collection coverage, status
  counts, and sector-level missingness.
- [`outputs/requirement_audit.json`](outputs/requirement_audit.json): structural audit showing
  whether the Part 2 data contract is satisfied.
- [`data/review/manual_review_queue.csv`](data/review/manual_review_queue.csv): missing or
  review-needed company-years.
- [`outputs/text_mining/`](outputs/text_mining/): deterministic text-mining CSVs, figures, and
  Markdown/LaTeX tables.
- [`outputs/text_mining/enhanced/`](outputs/text_mining/enhanced/): exploratory open-source model
  outputs, including NMF topics, MiniLM embedding shifts, spaCy features, and sampled local LLM
  annotations.
- [`src/org_auth_part2/`](src/org_auth_part2/): reproducible collection, extraction, analysis,
  presentation, and validation code.
- [`tests/`](tests/): tests for target construction, EDGAR selection, extraction, analysis,
  status reporting, enhanced analysis, and validation.

The local audit-only artifacts are:

- `outputs/part2_company_year.csv`: full dataset including extracted text. It is intentionally
  ignored by Git because it is large and reproducible from SEC.
- `data/raw/filings/`: downloaded SEC primary filing documents.
- `data/processed/text/`: full extracted text artifacts.
- `data/interim/*.jsonl` and state/cache files: useful for run monitoring and audit, but not the
  lightweight reviewer-facing dataset.

## Commands

The commands below reproduce the Part 2 collection and analysis from the repository root. Use
`PYTHONPATH` so Part 2 can run without changing the root package config.

Install the shared root `uv` environment:

```bash
uv sync
```

Create the 50-company by 2016-2024 target grid:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.targets
```

Optional smoke run against a few real SEC rows:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.run --ticker AAPL,MSFT --limit 4
```

Run the full SEC collection. This downloads `DEF 14A` primary documents, extracts text, writes
hashes, computes deterministic theme evidence, and emits the company-year datasets:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.run
```

Monitor a long collection run from another terminal:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.status
```

Validate the collected dataset and audit files:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.validate
```

Generate deterministic text-mining summaries and the main analysis draft:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.text_mining
```

Generate deterministic figures:

```bash
PYTHONPATH=part2_lived_values/src \
MPLCONFIGDIR=part2_lived_values/data/interim/matplotlib \
  uv run --no-sync python -m org_auth_part2.figures
```

Generate Markdown/LaTeX tables and refresh the written analysis:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.presentation
```

Generate enhanced open-source model checks. This uses TF-IDF/NMF, MiniLM embeddings, spaCy, and a
sampled local FLAN-T5 annotation pass:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.enhanced_text_mining --enable-llm --seed 42
```

Generate enhanced figures/tables and insert them into the main analysis:

```bash
PYTHONPATH=part2_lived_values/src \
MPLCONFIGDIR=part2_lived_values/data/interim/matplotlib \
  uv run --no-sync python -m org_auth_part2.enhanced_presentation
```

Run final tests and lint:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync pytest part2_lived_values/tests

PYTHONPATH=part2_lived_values/src \
  uv run --no-sync ruff check part2_lived_values/src/org_auth_part2 part2_lived_values/tests
```

## Live Progress

The runner writes:

- `data/interim/part2_run_progress.jsonl`: event log with run, target, download, and extraction status.
- `data/interim/part2_run_state.json`: latest completed target and count.
- `outputs/coverage_report.json`: status counts and coverage rate.
- `outputs/requirement_audit.json`: structural audit for the Part 2 contract.

The status command reads the JSONL log and state file, so a long run can be monitored while it is
still active.

## Success Evidence

A successful collected row must have:

- SEC CIK
- accession number
- filing date
- SEC archive URL
- local raw filing artifact
- raw filing byte size
- raw content SHA256
- clean text SHA256
- extracted word and sentence counts
- extraction quality marked `usable`
- theme and linguistic metrics computed with the Part 1-compatible taxonomy

Rows that fail any of these checks are not silently dropped; they remain in the dataset with a
controlled status and gap reason.
