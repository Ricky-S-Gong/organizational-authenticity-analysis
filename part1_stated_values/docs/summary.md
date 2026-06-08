# Part 1 Summary

## Scope

The pipeline evaluated all 450 required company-year targets across 50 companies and 2016–2024.

## Coverage

- Target grid coverage: 450 of 450 required company-years were
  processed (50 companies, 2016-2024).
- CDX discovery coverage: 450 of 450 company-years completed with no
  `discovery_incomplete` rows.
- Snapshot selection coverage: 385 of 450 company-years had a selected
  replayable Wayback snapshot; 60 had no CDX capture
  and 5 had captures but no eligible replayable
  capture under the locked rules.
- Replay/extraction coverage: 385 selected snapshots were attempted, producing
  370 cached/fetched text artifacts and
  15 final retrieval failures.
- Usable analytical records: 358 of
  450 company-years (79.6%);
  50 of 50 companies have at least one usable record.
- Companies represented in the final grid: 50. Non-usable
  company-years remain in the final output with explicit gap reasons.
- Local LLM coverage: 358 usable snapshots received model-generated notes, and
  299 adjacent usable company-year pairs received model-generated change notes.

Status breakdown:

- `insufficient_substantive_text`: 12
- `no_cdx_capture`: 60
- `no_eligible_capture`: 5
- `retrieval_failed`: 15
- `usable`: 358

Usable records by year:

- 2016: 29 of 50
- 2017: 36 of 50
- 2018: 36 of 50
- 2019: 38 of 50
- 2020: 41 of 50
- 2021: 44 of 50
- 2022: 44 of 50
- 2023: 44 of 50
- 2024: 46 of 50

Usable records by sector:

- Consumer Discretionary: 68 of 90
- Energy: 64 of 90
- Financials: 83 of 90
- Healthcare: 73 of 90
- Technology: 70 of 90

## Method

For each reviewed candidate page, the pipeline queried the Wayback CDX API and selected the
successful HTML capture nearest June 30 of the target year. It extracted substantive visible
text, computed adjacent-year change metrics, and applied an evidence-backed fixed theme taxonomy.
It also ran a cached local `Qwen/Qwen3-1.7B` causal-chat analysis layer over usable snapshots and
adjacent usable pairs, preserving prompt/response hashes, model parameters, device metadata, and
quality flags.

## Interpretation

The outputs are a reproducible analytical baseline with completed extraction/gap adjudication
records. Missing or unusable captures are reported as gaps and are never interpreted as absence of
organizational values.

## Limitation

Theme and linguistic outputs use a transparent deterministic baseline for row-level reproducibility.
The local Qwen LLM layer is included for transparency and audit triage; the deterministic baseline
remains the primary evidence used for structured claims.
