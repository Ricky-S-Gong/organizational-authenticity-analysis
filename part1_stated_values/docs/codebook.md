# Part 1 Data Codebook

## Required Final Fields

| Field | Meaning |
|---|---|
| `ticker` | Required company ticker |
| `company_name` | Required company name |
| `sector` | Required GICS sector grouping |
| `year` | Target calendar year, 2016–2024 |
| `page_text_clean` | Extracted substantive body text |
| `changed_from_prior` | Whether cleaned text changed substantively from the immediately prior year; null when comparison is unavailable |
| `theme_categories` | Evidence-backed multi-label theme categories |
| `analyst_notes` | Concise interpretation and limitations |

## Provenance and Quality Fields

| Field | Meaning |
|---|---|
| `observation_status` | Controlled collection/extraction status |
| `gap_reason` | Structured explanation for non-usable rows |
| `candidate_url` | Reviewed URL used in CDX discovery |
| `source_url` | Original archived URL |
| `wayback_url` | Replay URL for the selected capture |
| `capture_timestamp` | Wayback capture timestamp |
| `selection_distance_days` | Distance from annual June 30 anchor |
| `raw_content_sha256` | Hash of replayed HTML |
| `clean_text_sha256` | Hash of cleaned substantive text |
| `extraction_quality` | Quality classification or score |
| `change_score` | Continuous adjacent-year change score |
| `change_magnitude` | Interpretable change class |
| `manual_review_status` | Whether human review is pending or complete |
