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

Parts 1, 2, and 3 are complete and validated. Part 4 has not started yet.

| Part | Status | Current evidence |
| --- | --- | --- |
| [Part&nbsp;1:&nbsp;Stated&nbsp;Values](part1_stated_values/) | Complete | 450/450 company-years processed; 358 usable archived stated-values pages; Phase 0-7 validation passes. |
| [Part&nbsp;2:&nbsp;Lived&nbsp;Values](part2_lived_values/) | Complete | 450/450 company-years processed; 434 SEC `DEF 14A` filings collected; validation passes. |
| [Part&nbsp;3:&nbsp;Authenticity&nbsp;Index](part3_authenticity/) | Complete | 450-row authenticity panel; 328 scored company-years; semantic robustness, scatter diagnostics, qualitative audit notes, figures, validity, and sensitivity outputs generated. |
| [Part&nbsp;4:&nbsp;Proposal](part4_proposal/) | Not started | To be selected after Part 3 results expose interpretable patterns and limitations. |

## Repository Structure

```text
.
├── part1_stated_values/   # Wayback Machine collection and stated-values analysis
├── part2_lived_values/    # SEC DEF 14A collection and lived-values disclosure analysis
├── part3_authenticity/    # Organizational Authenticity Index
├── part4_proposal/        # Additional exploratory analysis
├── pyproject.toml         # Project and tool configuration
├── uv.lock                # Locked Python environment
└── README.md
```

Each completed part is self-contained with its own README, source code, tests, output data, and
written summary.

## Key Deliverables

### Part 1: Stated Values

- [Part 1 deliverables](part1_stated_values/README.md#deliverables)

### Part 2: Lived Values

- [Part 2 deliverables](part2_lived_values/README.md#deliverables)

The full Part 2 extracted-text dataset and raw SEC filings are reproducible local artifacts. They
may be omitted from Git in smaller submissions because of size, while the compact dataset retains
source, hash, theme, and metric fields.

### Part 3: Organizational Authenticity Index

- [Part 3 deliverables](part3_authenticity/README.md#deliverables)

### Part 4: Proposal

- Not started yet; deliverables will be listed in the Part 4 README once the proposal direction is selected.

## Setup

Clone the repository and install the shared `uv` environment:

```bash
git clone https://github.com/Ricky-S-Gong/organizational-authenticity-analysis.git
cd organizational-authenticity-analysis
uv sync
```

Run the default root checks. The root `pytest` configuration currently points to the Part 1 test
suite, while `ruff check .` scans the repository:

```bash
uv run --no-sync pytest
uv run --no-sync ruff check .
```

Run focused checks when working on a specific later part:

```bash
PYTHONPATH=part2_lived_values/src \
  uv run --no-sync pytest part2_lived_values/tests

PYTHONPATH=part2_lived_values/src \
  uv run --no-sync ruff check part2_lived_values/src/org_auth_part2 part2_lived_values/tests

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.validate

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync pytest part3_authenticity/tests

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync ruff check part3_authenticity/src/org_auth_part3 part3_authenticity/tests
```

## Part-Level Commands

Detailed reproduction commands live in each part's README:

- [Part 1 commands](part1_stated_values/README.md#commands)
- [Part 2 commands](part2_lived_values/README.md#commands)
- [Part 3 commands](part3_authenticity/README.md#commands)

## Data and Interpretation Notes

- The fixed company sample is defined in [part1_stated_values/config/companies.csv](part1_stated_values/config/companies.csv).
- Part 1 and Part 2 use the same deterministic theme taxonomy
  (`1.0.0-keyword-baseline`) so their outputs can be compared in Part 3.
- Missing company-years are retained with explicit status and gap reasons rather than silently
  dropped or imputed.
- The Part 3 index currently scores 328 company-years with sufficient stated-values and disclosure
  theme evidence, with semantic similarity, sector percentile, and sector z-score diagnostics.
- Proxy statements are treated as official disclosure evidence, not direct observations of
  corporate behavior. That construct-validity caveat carries into the authenticity index.
