# Part 2 Execution Plan

## Objective

Build a free, reproducible, auditable Part 2 pipeline for lived-value disclosures.

## Plan

1. Create the 50-company by 2016-2024 target grid from the fixed Part 1 company sample.
2. Use SEC EDGAR `DEF 14A` proxy statements as the single disclosure type.
3. Resolve ticker to CIK through the official SEC ticker map.
4. Pull SEC submissions JSON for each company and select the calendar-year `DEF 14A`.
5. Download the selected primary filing document from SEC Archives.
6. Store raw artifacts, clean text, source metadata, and SHA256 hashes.
7. Apply Part 1-compatible theme and linguistic analysis.
8. Emit a structured company-year dataset, candidate metadata, coverage report, audit report, and
   manual review queue.
9. Maintain a JSONL progress log and state file so long runs can be monitored.
10. Verify both code behavior with tests and real-data collection with a smoke run.

## Acceptance Criteria

- All Part 2 files live inside `part2_lived_values/`.
- The target grid has 450 company-year rows for 50 companies and 2016-2024.
- Every row has a controlled collection status and gap reason when applicable.
- Every collected row has SEC URL, CIK, accession number, raw hash, clean hash, word count, and
  extraction quality.
- Tests cover target construction, EDGAR selection, extraction, analysis, status, and validation.
- A smoke run demonstrates at least one real SEC filing collected with non-empty text and hashes.

