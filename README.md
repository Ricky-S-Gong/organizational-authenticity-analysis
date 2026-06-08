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

Parts 1, 2, 3, and 4 are complete and validated. A root-level LaTeX manuscript synthesizes the
pipeline and findings as an academic-style report, while the part directories retain the
assignment-specific code, outputs, README files, summaries, and validation audits.

| Part | Status | Current evidence |
| --- | --- | --- |
| [Part&nbsp;1:&nbsp;Stated&nbsp;Values](part1_stated_values/) | Complete | 450/450 company-years processed; 358 usable archived stated-values pages; Phase 0-7 validation passes. |
| [Part&nbsp;2:&nbsp;Lived&nbsp;Values](part2_lived_values/) | Complete | 450/450 company-years processed; 434 SEC `DEF 14A` filings collected; validation passes. |
| [Part&nbsp;3:&nbsp;Authenticity&nbsp;Index](part3_authenticity/) | Complete | 450-row authenticity panel; 328 scored company-years; semantic robustness, scatter diagnostics, qualitative audit notes, figures, validity, and sensitivity outputs generated. |
| [Part&nbsp;4:&nbsp;Proposal](part4_proposal/) | Complete | Proxy-genre sensitivity, section-level proxy parsing, theme-level semantic comparison, figures, tests, and validation generated. |

## Assessment Compliance Checklist

| Requirement | Repository evidence |
| --- | --- |
| Structured repository with commented code | Each part has `src/`, `tests/`, `docs/`, and outputs; Part 4 code includes method-level docstrings and inline comments for phrase counting, section parsing, semantic fallback, and figure encodings. |
| README per part | `part1_stated_values/README.md`, `part2_lived_values/README.md`, `part3_authenticity/README.md`, and `part4_proposal/README.md`. |
| Output data files | Each part has committed compact outputs and requirement audits under its `outputs/` directory. |
| Written summary per part | Each part includes `docs/summary.md`; the root manuscript provides a single integrated report. |
| Part 1 Wayback stated-values collection | 450 target company-years retained; 358 usable stated-values pages; missingness and acquisition status documented. |
| Part 2 lived-values disclosure analysis | SEC `DEF 14A` proxy statements collected as the lived-values disclosure source; 434 filings collected with text-mining outputs and coverage notes. |
| Part 3 authenticity measure | 450-row panel with 328 scoreable company-years, distribution summaries, validity checks, sensitivity metrics, and case-audit notes. |
| Part 4 proposal and implementation | Proxy-genre pressure, section-level proxy parsing, theme-level semantic comparison, case-audit targets, figures, tests, and validation audit. |

## Repository Structure

```text
.
├── part1_stated_values/   # Wayback Machine collection and stated-values analysis
├── part2_lived_values/    # SEC DEF 14A collection and lived-values disclosure analysis
├── part3_authenticity/    # Organizational Authenticity Index
├── part4_proposal/        # Additional exploratory analysis
├── manuscript.tex         # Root-level LaTeX manuscript synthesizing Parts 1-4
├── manuscript.pdf         # Compiled manuscript
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

### Part 3: Organizational Authenticity Index

- [Part 3 deliverables](part3_authenticity/README.md#deliverables)

### Part 4: Proposal

- [Part 4 deliverables](part4_proposal/README.md#deliverables)

### Manuscript

- [Manuscript PDF](manuscript.pdf)

### Notes

Some raw, full-text, cache, model, and intermediate artifacts are reproducible local files and may
be omitted from Git because of size. The committed compact outputs retain source links, hashes,
theme evidence, metrics, and audit files needed to verify the submitted results.

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

PYTHONPATH=part4_proposal/src \
  uv run --no-sync python -m org_auth_part4.validate

PYTHONPATH=part4_proposal/src \
  uv run --no-sync pytest part4_proposal/tests

PYTHONPATH=part4_proposal/src \
  uv run --no-sync ruff check part4_proposal/src/org_auth_part4 part4_proposal/tests
```

## Part-Level Commands

Detailed reproduction commands live in each part's README:

- [Part 1 commands](part1_stated_values/README.md#commands)
- [Part 2 commands](part2_lived_values/README.md#commands)
- [Part 3 commands](part3_authenticity/README.md#commands)
- [Part 4 commands](part4_proposal/README.md#commands)

## Data and Interpretation Notes

- The fixed company sample is defined in [part1_stated_values/config/companies.csv](part1_stated_values/config/companies.csv).
- Part 1 and Part 2 use the same deterministic theme taxonomy
  (`1.0.0-keyword-baseline`) so their outputs can be compared in Part 3.
- Missing company-years are retained with explicit status and gap reasons rather than silently
  dropped or imputed.
- The Part 3 index currently scores 328 company-years with sufficient stated-values and disclosure
  theme evidence, with semantic similarity, sector percentile, and sector z-score diagnostics.
- The Part 4 case-audit output now defines case types with the two primary alignment diagnostics
  (`OAI` and whole-text semantic similarity); proxy genre pressure remains an auxiliary diagnostic
  column rather than a case-type criterion.
- Proxy statements are treated as official disclosure evidence, not direct observations of
  corporate behavior. That construct-validity caveat carries into the authenticity index.
