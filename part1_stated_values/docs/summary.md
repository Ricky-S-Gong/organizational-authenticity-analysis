# Part 1 Summary

## Scope

The pipeline evaluated all 450 required company-year targets across 50 companies and 2016–2024.

## Coverage

- Usable records: 14 of 450 (3.1%)
- Companies represented: 50

Status breakdown:

- `discovery_incomplete`: 397
- `insufficient_substantive_text`: 6
- `no_cdx_capture`: 14
- `no_eligible_capture`: 10
- `no_eligible_page`: 9
- `usable`: 14

## Method

For each reviewed candidate page, the pipeline queried the Wayback CDX API and selected the
successful HTML capture nearest June 30 of the target year. It extracted substantive visible
text, computed adjacent-year change metrics, and applied an evidence-backed fixed theme taxonomy.

## Interpretation

The outputs are a reproducible analytical baseline. Selected-page identity, flagged extractions,
change events, and theme assignments require human review before substantive claims are finalized.
Missing captures are reported as gaps and are never interpreted as absence of organizational values.

## Limitation

No external LLM credentials were available during this run. Theme and linguistic outputs use a
transparent deterministic baseline; an LLM-assisted extension must record model, prompt, input
hashes, and validation results before being reported.
