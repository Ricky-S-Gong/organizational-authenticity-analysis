# Extraction Validation

## Decision

Extraction and gap adjudication are complete for the current Part 1 run.

## Evidence

- Completed extraction/gap review decisions: 450.
- Usable records: 155 of 450.
- Unresolved manual review queue rows: 0.

Status breakdown:

- `insufficient_substantive_text`: 93
- `no_cdx_capture`: 144
- `no_eligible_capture`: 49
- `no_eligible_page`: 9
- `usable`: 155

## Rule

Usable records retain source URL, Wayback URL, capture timestamp, raw SHA-256, clean-text
SHA-256, extraction quality, theme evidence, and linguistic metrics. Non-usable records are
kept in the panel as explicit gaps and excluded from substantive values interpretation.
