# Part 4: Proxy-Genre Sensitivity

Part 4 proposes and implements an exploratory measurement-diagnostic analysis for the Part 3
Organizational Authenticity Index.

## What I Did

I tested whether low authenticity-index scores are partly explained by the genre and structure of
the Part 2 `DEF 14A` proxy statements. The analysis now has three layers:

- a whole-document proxy-genre pressure diagnostic;
- a section-level proxy parser showing where values-theme evidence appears;
- a theme-level semantic comparison of Part 1 and Part 2 evidence excerpts inside each shared
  taxonomy theme.

The goal is not to replace the Part 3 index. It is to identify when the index may be affected by
the proxy-statement genre, which sections drive disclosure-side theme evidence, and whether shared
theme labels carry similar local meaning across stated-values pages and proxy statements.

The qualitative case-audit output uses the two primary alignment diagnostics--the Organizational
Authenticity Index (OAI) and whole-text semantic similarity (SS)--to define case types. Proxy genre
pressure is retained as an auxiliary interpretation column rather than as a case-type criterion.

## Why This Design

Parts 2 and 3 already acknowledge that proxy statements are official disclosure artifacts, not
direct observations of behavior. This Part 4 extension turns that limitation into a research
question: does the authenticity index look robust to proxy-statement genre pressure, or do low
scores cluster in highly procedural proxy documents?

The design stays deterministic and auditable. It uses existing Part 1, Part 2, and Part 3 outputs,
does not collect new company data, retains all 450 company-years where applicable, and marks
unavailable rows with explicit status fields.

## Assumptions

- `DEF 14A` proxy statements are comparable official disclosures but are shaped by legal and
  governance reporting conventions.
- Transparent phrase dictionaries and heading heuristics are sufficient for a preliminary
  section-level diagnostic.
- Same-theme evidence excerpts are a useful local semantic unit for comparing stated and disclosed
  values language.
- Genre pressure is a measurement-risk signal, not proof that a proxy statement is boilerplate,
  misleading, or substantively weak.
- Missing proxy text should remain missing rather than being imputed.

## Known Limitations

- The phrase dictionaries are incomplete and can count substantive governance discussion as genre
  language.
- The analysis is descriptive and exploratory; it does not estimate a causal effect of proxy genre,
  section placement, or semantic similarity on authenticity scores.
- The section parser is heuristic and can split filings too finely when extracted text contains
  many table-of-contents or layout fragments.
- Theme-level semantic comparison depends on upstream evidence excerpts, so it inherits dictionary
  recall limits from Parts 1 and 2.

## What I Would Do Differently With More Time

- Recompute the authenticity index after downweighting meeting mechanics and voting instructions.
- Validate the genre dictionaries on a manually annotated sample.
- Validate section headings and theme-semantic matches on a manually annotated sample.
- Compare proxy-statement diagnostics with an alternative official source, such as 10-K
  human-capital sections.

## Deliverables

- [`docs/summary.md`](docs/summary.md): concise nontechnical summary of the research question,
  method, findings, and limitations.
- [`docs/methodology.md`](docs/methodology.md): construct definition, workflow, formulas, and
  interpretation rules.
- [`docs/codebook.md`](docs/codebook.md): column definitions for the diagnostic dataset and
  supporting outputs.
- [`outputs/part4_genre_diagnostics.csv`](outputs/part4_genre_diagnostics.csv): 450-row diagnostic
  panel.
- [`outputs/genre_pressure_summary.csv`](outputs/genre_pressure_summary.csv): overall and tercile
  summaries.
- [`outputs/genre_pressure_correlations.csv`](outputs/genre_pressure_correlations.csv): correlation
  diagnostics.
- [`outputs/quadrant_genre_summary.csv`](outputs/quadrant_genre_summary.csv): genre pressure by
  keyword-semantic quadrant.
- [`outputs/case_audit_targets.csv`](outputs/case_audit_targets.csv): qualitative audit targets.
  Case buckets are `low_oai_low_ss`, `low_oai_high_ss`, `high_oai_low_ss`, and `high_oai_high_ss`.
- [`outputs/genre_pressure_regression.csv`](outputs/genre_pressure_regression.csv): descriptive
  regression coefficients.
- [`outputs/section_diagnostics.csv`](outputs/section_diagnostics.csv): long-format parsed proxy
  section diagnostics.
- [`outputs/section_summary.csv`](outputs/section_summary.csv): section-family contribution
  summary.
- [`outputs/theme_level_semantic_similarity.csv`](outputs/theme_level_semantic_similarity.csv):
  theme-by-company-year local semantic comparison.
- [`outputs/theme_level_semantic_summary.csv`](outputs/theme_level_semantic_summary.csv): aggregate
  theme-level semantic summary.
- [`outputs/requirement_audit.json`](outputs/requirement_audit.json): structural validation audit.
- [`outputs/figures/`](outputs/figures/): diagnostic figures, including genre-pressure plots,
  section-family/theme visualizations, and theme-level semantic gap plots.

## Commands

Run the full Part 4 analysis from the repository root:

```bash
PYTHONPATH=part4_proposal/src \
  uv run --no-sync python -m org_auth_part4.analysis

PYTHONPATH=part4_proposal/src \
  uv run --no-sync python -m org_auth_part4.sections

PYTHONPATH=part4_proposal/src \
  uv run --no-sync python -m org_auth_part4.theme_semantic

PYTHONPATH=part4_proposal/src \
MPLCONFIGDIR=part4_proposal/outputs/matplotlib \
  uv run --no-sync python -m org_auth_part4.figures

PYTHONPATH=part4_proposal/src \
  uv run --no-sync python -m org_auth_part4.presentation

PYTHONPATH=part4_proposal/src \
  uv run --no-sync python -m org_auth_part4.validate
```

Run tests and lint:

```bash
PYTHONPATH=part4_proposal/src \
  uv run --no-sync pytest part4_proposal/tests

PYTHONPATH=part4_proposal/src \
  uv run --no-sync ruff check part4_proposal/src/org_auth_part4 part4_proposal/tests
```
