# Part 1 Summary

## Scope

The pipeline evaluated all 450 required company-year targets across 50 companies and 2016–2024.

## Coverage

- Usable records: 155 of 450 (34.4%)
- Companies represented: 50

Status breakdown:

- `insufficient_substantive_text`: 93
- `no_cdx_capture`: 144
- `no_eligible_capture`: 49
- `no_eligible_page`: 9
- `usable`: 155

## Method

For each reviewed candidate page, the pipeline queried the Wayback CDX API and selected the
successful HTML capture nearest June 30 of the target year. It extracted substantive visible
text, computed adjacent-year change metrics, and applied an evidence-backed fixed theme taxonomy.

## Interpretation

The outputs are a reproducible analytical baseline with completed extraction/gap adjudication
records. Missing or unusable captures are reported as gaps and are never interpreted as absence of
organizational values.

## Limitation

Theme and linguistic outputs use a transparent deterministic baseline for row-level reproducibility.
An external LLM-assisted extension can be added later as a robustness check if model, prompt, input
hashes, and validation results are recorded.
