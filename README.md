# Organizational Authenticity Assessment

This repository contains the work for the Wharton-TAU Lab 2026 Research Assistant recruitment
assignment on organizational authenticity and corporate value alignment. The project studies the
same fixed sample of 50 large S&P 500 firms across Technology, Financials, Healthcare, Consumer
Discretionary, and Energy from 2016 through 2024.

The research pipeline is organized around the assignment's four parts:

1. **Stated values:** archived corporate About, mission, purpose, and values pages.
2. **Lived values:** one auditable disclosure source, implemented here as SEC `DEF 14A` proxy
   statements.
3. **Organizational authenticity index:** an alignment measure using the Part 1 and Part 2 outputs.
4. **Additional analysis:** a short exploratory extension using the index or source data.

## Project Status

The repository currently contains implemented Part 1 and Part 2 pipelines plus their documentation,
tests, and generated outputs. Part 1 data collection is still being refreshed, so Part 3 planning
and implementation should wait until the final Part 1 coverage and gap profile are stable.

| Part | Status | Notes |
| --- | --- | --- |
| Part 1: Stated Values | Pipeline implemented; live collection/refresh in progress | Uses Wayback CDX discovery, deterministic annual snapshot selection, visible-text extraction, theme coding, and phase validation. |
| Part 2: Lived Values | Implemented | Uses SEC EDGAR `DEF 14A` proxy statements, deterministic theme/tone analysis, and enhanced exploratory NLP checks. |
| Part 3: Authenticity Index | Not started | Planned after final Part 1 outputs are available, using the shared Part 1/2 theme taxonomy. |
| Part 4: Proposal | Not started | To be selected after Part 3 reveals useful patterns and limitations. |

## Repository Structure

```text
.
├── part1_stated_values/   # Wayback Machine collection and stated-values analysis
├── part2_lived_values/    # Corporate disclosure collection and text analysis
├── part3_authenticity/    # Organizational Authenticity Index placeholder
├── part4_proposal/        # Additional analysis placeholder
├── docs/                  # Assignment reference materials and internal planning notes
├── pyproject.toml         # Project and tool configuration
├── uv.lock                # Locked Python environment
└── README.md
```

Each completed part is self-contained with its own README, source code, tests, output data, and
written summary.

## Key Deliverables

### Part 1

- `part1_stated_values/README.md`: Part 1 workflow, commands, and data policy
- `part1_stated_values/outputs/part1_company_year.csv`: final company-year dataset
- `part1_stated_values/outputs/theme_observations.csv`: long-format theme evidence
- `part1_stated_values/outputs/coverage_report.json`: collection and extraction coverage
- `part1_stated_values/outputs/phase_validation.json`: phase completion checks
- `part1_stated_values/docs/summary.md`: written summary
- `part1_stated_values/docs/taxonomy.md`: fixed theme taxonomy

### Part 2

- `part2_lived_values/README.md`: Part 2 workflow, commands, and data policy
- `part2_lived_values/outputs/part2_company_year_compact.csv`: git-friendly company-year dataset
- `part2_lived_values/outputs/coverage_report.json`: SEC collection coverage
- `part2_lived_values/docs/text_mining_analysis.md`: main text-mining report
- `part2_lived_values/docs/summary.md`: written summary
- `part2_lived_values/docs/codebook.md`: output schema and column definitions
- `part2_lived_values/outputs/text_mining/`: deterministic tables and figures
- `part2_lived_values/outputs/text_mining/enhanced/`: exploratory open-source NLP outputs

The full Part 2 extracted-text dataset and raw SEC filings are reproducible local artifacts and may
be omitted from Git because of size.

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

Monitor a long Part 1 run:

```bash
uv run --no-sync part1-run-status
```

Validate Part 1 phase gates:

```bash
uv run --no-sync part1-validate-phases
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

## Data and Interpretation Notes

- The fixed company sample is defined in `part1_stated_values/config/companies.csv`.
- Part 1 and Part 2 use the same deterministic theme taxonomy
  (`1.0.0-keyword-baseline`) so their outputs can later be compared in Part 3.
- Missing company-years are retained with explicit status and gap reasons rather than silently
  dropped or imputed.
- Proxy statements are treated as official disclosure evidence, not direct observations of
  corporate behavior. That construct-validity caveat should carry into Part 3.
