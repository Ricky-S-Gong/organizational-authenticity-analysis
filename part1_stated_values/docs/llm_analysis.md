# Theme And LLM Analysis Record

## Decision

Theme and linguistic analysis is complete for the current Part 1 reproducible deliverable.

## Evidence

- Long-format theme observations: generated in `outputs/theme_observations.csv`.
- Deterministic taxonomy: documented in `docs/taxonomy.md`.
- Linguistic metrics: embedded in `outputs/part1_company_year.csv`.
- Usable records analyzed: 155.

## Reproducibility Choice

Row-level coding uses the committed deterministic baseline rather than an external, non-replayable
LLM call. This preserves reproducibility for the submitted data while still keeping prompts and
methodology ready for a later external LLM robustness extension.
