# Organizational Authenticity Assessment

This repository contains the Wharton-TAU Lab 2026 Research Assistant assignment on organizational
authenticity and corporate value alignment. The project studies a fixed sample of 50 large S&P 500
firms across Technology, Financials, Healthcare, Consumer Discretionary, and Energy from 2016
through 2024.

The research pipeline is organized around four parts:

1. **Stated values:** archived corporate About, mission, purpose, and values pages.
2. **Lived values:** one auditable disclosure source, implemented here as SEC `DEF 14A` proxy
   statements.
3. **Organizational authenticity index:** an alignment measure using the Part 1 and Part 2 outputs.
4. **Additional analysis:** a short exploratory extension using the index or source data.

## Project Status

Parts 1 and 2 are complete and validated. Part 3 is in progress and can now use the final Part 1
and Part 2 outputs.

| Part | Status | Current evidence |
| --- | --- | --- |
| [Part 1: Stated Values](part1_stated_values/) | Complete | 450/450 company-years processed; 358 usable archived stated-values pages; Phase 0-7 validation passes. |
| [Part 2: Lived Values](part2_lived_values/) | Complete | 450/450 company-years processed; 434 SEC `DEF 14A` filings collected; validation passes. |
| [Part 3: Authenticity Index](part3_authenticity/) | In progress | Part 1/2 overlap provides 342 company-years with both usable stated-values text and collected proxy disclosures. |
| [Part 4: Proposal](part4_proposal/) | Not started | To be selected after Part 3 exposes interpretable patterns and limitations. |

## Repository Structure

```text
.
├── part1_stated_values/   # Wayback Machine collection and stated-values analysis
├── part2_lived_values/    # SEC DEF 14A collection and lived-values disclosure analysis
├── part3_authenticity/    # Organizational Authenticity Index
├── part4_proposal/        # Additional exploratory analysis
├── docs/                  # Assignment reference materials and internal planning notes
├── pyproject.toml         # Project and tool configuration
├── uv.lock                # Locked Python environment
└── README.md
```

Each completed part is self-contained with its own README, source code, tests, output data, and
written summary.

## Key Deliverables

### Part 1: Stated Values

- [Part 1 README](part1_stated_values/README.md): workflow, assumptions, commands, and data policy
- [Summary](part1_stated_values/docs/summary.md): concise written summary
- [Methodology](part1_stated_values/docs/methodology.md): Wayback page selection, extraction, and validation design
- [Validation report](part1_stated_values/docs/validation_report.md): Phase 0-7 status and evidence
- [Codebook](part1_stated_values/docs/codebook.md): dataset columns and script task map
- [Theme taxonomy](part1_stated_values/docs/taxonomy.md): fixed `1.0.0-keyword-baseline` taxonomy
- [Final company-year dataset](part1_stated_values/outputs/part1_company_year.csv): 450-row panel
- [Theme observations](part1_stated_values/outputs/theme_observations.csv): long-format phrase evidence
- [Change events](part1_stated_values/outputs/change_events.csv): adjacent-year change classifications
- [Coverage report](part1_stated_values/outputs/coverage_report.json): usable/gap counts
- [Phase validation](part1_stated_values/outputs/phase_validation.json): machine-readable completion gates
- [Requirement audit](part1_stated_values/outputs/requirement_audit.json): structural audit output
- [LLM snapshot notes](part1_stated_values/outputs/llm_analysis/llm_snapshot_analysis.csv): local Qwen notes for usable rows
- [LLM change notes](part1_stated_values/outputs/llm_analysis/llm_change_analysis.csv): local Qwen notes for adjacent usable pairs
- [LLM analysis manifest](part1_stated_values/outputs/llm_analysis/llm_analysis_summary.json): model, prompt, hash, and quality metadata

### Part 2: Lived Values

- [Part 2 README](part2_lived_values/README.md): workflow, assumptions, commands, and data policy
- [Summary](part2_lived_values/docs/summary.md): concise written summary
- [Methodology](part2_lived_values/docs/methodology.md): SEC source choice, selection rule, extraction, and analysis design
- [Text-mining analysis](part2_lived_values/docs/text_mining_analysis.md): main report with figures and tables
- [Codebook](part2_lived_values/docs/codebook.md): dataset columns and script task map
- [Audit notes](part2_lived_values/docs/audit_notes.md): methodological audit of the SEC `DEF 14A` approach
- [Top shift excerpt audit](part2_lived_values/docs/top_shift_excerpt_audit.md): qualitative review of selected large shifts
- [Execution plan](part2_lived_values/docs/plan.md): original implementation plan and acceptance criteria
- [Compact company-year dataset](part2_lived_values/outputs/part2_company_year_compact.csv): 450-row git-friendly dataset
- [Full company-year dataset](part2_lived_values/outputs/part2_company_year.csv): local full dataset with extracted proxy text
- [Coverage report](part2_lived_values/outputs/coverage_report.json): SEC collection status counts
- [Requirement audit](part2_lived_values/outputs/requirement_audit.json): structural audit output
- [Text-mining summary](part2_lived_values/outputs/text_mining/text_mining_summary.json): deterministic analysis manifest
- [Theme-year summary](part2_lived_values/outputs/text_mining/theme_year_summary.csv): theme rates over time
- [Theme-sector summary](part2_lived_values/outputs/text_mining/theme_sector_summary.csv): sector variation
- [Company theme trends](part2_lived_values/outputs/text_mining/company_theme_trends.csv): company-level theme trajectories
- [Event-window summary](part2_lived_values/outputs/text_mining/event_window_summary.csv): 2020-2021 event-window comparisons
- [Linguistic year summary](part2_lived_values/outputs/text_mining/linguistic_year_summary.csv): tone/style trends by year
- [Sector linguistic summary](part2_lived_values/outputs/text_mining/sector_linguistic_summary.csv): tone/style variation by sector
- [Top adjacent theme shifts](part2_lived_values/outputs/text_mining/top_adjacent_theme_shifts.csv): largest within-company theme moves
- [Missingness summary](part2_lived_values/outputs/text_mining/missing_summary.csv): missing company-years
- [Text-mining tables](part2_lived_values/outputs/text_mining/tables/): Markdown and LaTeX tables
- [Text-mining figures](part2_lived_values/outputs/text_mining/figures/): PNG and SVG figures
- [Enhanced text-mining manifest](part2_lived_values/outputs/text_mining/enhanced/enhanced_text_mining_summary.json): open-source model-check metadata
- [NMF topics](part2_lived_values/outputs/text_mining/enhanced/nmf_topics.csv): exploratory topic model output
- [Document topic scores](part2_lived_values/outputs/text_mining/enhanced/document_topic_scores.csv): per-document NMF scores
- [Embedding manifest](part2_lived_values/outputs/text_mining/enhanced/embedding_manifest.csv): MiniLM embedding join keys
- [Embedding adjacent-year shifts](part2_lived_values/outputs/text_mining/enhanced/embedding_adjacent_year_shifts.csv): semantic-shift triage
- [spaCy features](part2_lived_values/outputs/text_mining/enhanced/spacy_features.csv): exploratory statistical NLP features
- [Local LLM annotations](part2_lived_values/outputs/text_mining/enhanced/llm_annotations.csv): sampled FLAN-T5 audit outputs

The full Part 2 extracted-text dataset and raw SEC filings are reproducible local artifacts. They
may be omitted from Git in smaller submissions because of size, while the compact dataset retains
source, hash, theme, and metric fields.

## Development

Install the shared environment:

```bash
uv sync
```

Run the repository-level Part 1 tests and lint:

```bash
uv run --no-sync pytest
uv run --no-sync ruff check .
```

Run Part 2 tests and lint:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync pytest part2_lived_values/tests

PYTHONPATH=part2_lived_values/src \
  uv run --no-sync ruff check part2_lived_values/src/org_auth_part2 part2_lived_values/tests
```

## Reproduction Commands

Run the Part 1 pipeline:

```bash
uv run --no-sync part1-run
```

Validate Part 1 phase gates:

```bash
uv run --no-sync part1-validate-phases
```

Run the local Part 1 LLM analysis layer:

```bash
uv run --no-sync part1-llm-analysis
```

Run the Part 2 SEC collection:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.run
```

Validate Part 2:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.validate
```

Generate Part 2 text-mining outputs:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.text_mining
```

Generate Part 2 figures and presentation tables:

```bash
PYTHONPATH=part2_lived_values/src \
MPLCONFIGDIR=part2_lived_values/data/interim/matplotlib \
  uv run --no-sync python -m org_auth_part2.figures

PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.presentation
```

Generate Part 2 enhanced open-source model checks:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync python -m org_auth_part2.enhanced_text_mining --enable-llm --seed 42
```

## Data and Interpretation Notes

- The fixed company sample is defined in [part1_stated_values/config/companies.csv](part1_stated_values/config/companies.csv).
- Part 1 and Part 2 use the same deterministic theme taxonomy
  (`1.0.0-keyword-baseline`) so their outputs can be compared in Part 3.
- Missing company-years are retained with explicit status and gap reasons rather than silently
  dropped or imputed.
- The Part 3 usable overlap currently contains 342 company-years with both usable stated-values
  text and collected `DEF 14A` disclosure.
- Proxy statements are treated as official disclosure evidence, not direct observations of
  corporate behavior. That construct-validity caveat carries into the authenticity index.
