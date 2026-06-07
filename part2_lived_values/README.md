# Part 2: Lived Values

Part 2 collects and analyzes lived-values disclosure for the same 50 companies and 2016-2024
company-year window used in Part 1.

## What I Did

I collected SEC `DEF 14A` proxy statements for the Part 1 company-year panel, extracted text,
computed theme and language/tone indicators, and generated the Part 2 dataset and analysis.

The final run covers 434 of 450 target company-years. The remaining 16 rows are retained as
documented missing observations rather than imputed or treated as zero disclosure.

## Why This Design

This pipeline uses SEC EDGAR `DEF 14A` proxy statements as the lived-values disclosure source.
Proxy statements are not direct observations of behavior, but they are official, free,
consistently archived, and highly reproducible. This makes them a stronger fit for an audited
proof-of-concept than manually collected ESG or sustainability PDFs.

The main analysis uses deterministic keyword/phrase matching and lexical metrics. Open-source
model checks are included only as exploratory triangulation.

## Assumptions

- A calendar-year `DEF 14A` filing is a comparable annual disclosure artifact for each company-year.
- The first calendar-year `DEF 14A` is the main proxy statement for that year; `DEFA14A`
  supplemental filings are excluded for comparability.
- Missing `DEF 14A` company-years are true collection gaps for this document type and should remain
  missing in downstream analysis.
- The Part 1-compatible keyword taxonomy is an auditable proxy for disclosed values language, not a
  complete model of organizational culture.
- Theme and tone rates should be normalized by document length because proxy statements vary
  substantially in size.

## Known Limitations

- Proxy statements are legal and governance documents, not direct observations of workplace or
  operational behavior.
- Dictionary matches can capture boilerplate or shareholder-proposal mechanics; large shifts require
  excerpt review.
- The fixed taxonomy can miss synonyms and context-specific meanings.
- Coverage is high but incomplete: 16 of 450 company-years are missing.

## What I Would Do Differently With More Time

- Expand excerpt-level validation with a larger manually reviewed sample across sectors and years.
- Add a second official disclosure type, such as 10-K human-capital sections, to compare whether
  proxy-statement patterns are document-type specific.
- Refine the taxonomy against a larger audit set and separate shareholder-meeting mechanics from
  substantive values language more explicitly.

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
- [`outputs/text_mining/`](outputs/text_mining/): deterministic text-mining CSVs, figures, and
  Markdown/LaTeX tables.
- [`outputs/text_mining/enhanced/`](outputs/text_mining/enhanced/): exploratory open-source model
  outputs, including NMF topics, MiniLM embedding shifts, spaCy features, and sampled local LLM
  annotations.

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
