# Part 2 SEC DEF 14A Pipeline Audit Notes

## Scope Reviewed

This note independently audits Part 2 method requirements against the assignment, the internal assessment analysis, the current Part 1 taxonomy, and the fixed company sample. It assumes Part 2 will use SEC EDGAR proxy statements (`DEF 14A`) as the single lived-values document type.

Files reviewed:

- `docs/reference/Research Assistant Recruitment Task - Wharton-TAU Lab 2026.md`
- `docs/internal/assessment_analysis.md`
- `part1_stated_values/docs/taxonomy.md`
- `part1_stated_values/config/companies.csv`
- `part1_stated_values/docs/codebook.md`
- `part1_stated_values/docs/methodology.md`
- `part1_stated_values/outputs/coverage_report.json`
- `part1_stated_values/outputs/requirement_audit.json`

## High-Level Assessment

DEF 14A is the best free, auditable, reproducible source choice for Part 2 because it is available through SEC EDGAR without paid access, has stable company identifiers, is date-stamped, and is legally archived. It is also scalable to all 50 companies and the 2016-2024 window.

The main validity caveat is construct validity: proxy statements are regulated disclosure documents, not direct behavioral observations. They can support claims about disclosed priorities, governance, compensation incentives, shareholder-facing accountability, board composition, and some human-capital or ESG language. They should not be framed as direct evidence of "actual lived values" without careful caveats.

The pipeline is automatable if it is built around CIK-based EDGAR metadata, deterministic filing selection rules, explicit company-year status records, and retained raw filing artifacts. A code test suite alone is insufficient; the final deliverable must include collection manifests, sample raw files, text extraction metrics, coverage tables, and validation artifacts proving that real SEC filings were collected and parsed.

## Automation Feasibility

Recommended source stack:

1. Use the SEC company tickers mapping to resolve each assignment ticker to CIK.
2. Normalize special tickers such as `BRK.B` to the SEC/company-ticker representation while retaining the original assignment ticker.
3. Query SEC submissions JSON for each CIK.
4. Filter filings to `form == "DEF 14A"` and filing dates within 2016-2024.
5. Map filings to fiscal/proxy year using a documented rule.
6. Download the primary filing document from SEC Archives.
7. Extract visible textual content from HTML filings, preserving sections and source provenance.
8. Produce one explicit row per target company-year, including rows where no DEF 14A was found.

Recommended annual selection rule:

- Target unit: one company-year for each of the 50 companies and years 2016-2024.
- Select the first `DEF 14A` filed in the target calendar year for that company, unless the filing is an amendment, duplicate, or non-annual special-meeting proxy.
- Exclude `DEFA14A`, `DEF 14C`, `PRE 14A`, and `DEFM14A` unless explicitly used only as fallback evidence with a distinct status.
- If multiple `DEF 14A` filings exist in a year, prefer the filing whose document title or meeting metadata indicates the annual meeting; otherwise prefer the earliest non-amended filing and flag `multiple_def14a_in_year`.
- Do not carry filings across years. If no target-year filing exists, record a non-usable status.

This rule is reproducible and avoids paid aggregators or company-IR pages. It also aligns with Part 1's company-year grid and missingness discipline.

## Key Risks

### Collection Risks

- Ticker-to-CIK drift: ticker changes, class-share notation, acquisitions, or issuer naming differences can silently map to the wrong registrant.
- Parent-company mismatch: some companies may file under a legal issuer name that differs from the common company name.
- Duplicate filings: multiple DEF 14A filings can appear for annual meetings, special meetings, supplements, or corrections.
- Form confusion: `DEFA14A`, `PRE 14A`, `DEF 14C`, and merger proxies are not equivalent to annual `DEF 14A`.
- Calendar-year ambiguity: a proxy filed in 2024 may describe fiscal year 2023 compensation and governance. The pipeline must choose and document whether the analysis year is filing year, meeting year, or fiscal year.
- SEC rate limits: requests need a descriptive user agent, throttling, retry handling, and resumable manifests.
- Network fragility: downloads can fail independently of metadata queries, so metadata discovery and document retrieval need separate statuses.

### Extraction Risks

- HTML structure varies across issuers and years.
- Tables can dominate proxy text, especially compensation tables.
- XBRL or inline markup may create duplicate text.
- Boilerplate legal language can swamp value-related language.
- PDFs or exhibits may be linked but not needed if the primary filing HTML is available.
- Very short extracted text often indicates parser failure, not substantive absence.

### Research Validity Risks

- Proxy statements overrepresent governance, compensation, shareholder rights, and board accountability relative to broader ESG or DEI behavior.
- Legal boilerplate and SEC disclosure norms may drive cross-company similarity.
- Board diversity disclosures became more common due to external pressures and rules; apparent value shifts may reflect regulation rather than internal value change.
- Raw word counts are not comparable across firms unless normalized by document length and, ideally, section.
- Part 1 categories are values-language categories, while proxy statements contain governance facts and compliance disclosures. Alignment should be framed as disclosure-priority alignment, not true authenticity.

## Required Status Fields

Every target company-year should have one status row, even if no usable document exists.

Minimum target identity fields:

- `ticker`
- `company_name`
- `sector`
- `year`
- `cik`
- `cik_source`
- `sec_company_name`
- `ticker_match_status`

Minimum collection status fields:

- `collection_status`: controlled values such as `usable`, `no_cik_match`, `no_def14a_in_year`, `multiple_candidates_review`, `download_failed`, `unsupported_document`, `extraction_failed`, `insufficient_text`
- `gap_reason`: non-null for every non-usable row
- `form_type`
- `accession_number`
- `filing_date`
- `report_or_meeting_date` when available
- `primary_document`
- `filing_detail_url`
- `primary_document_url`
- `selected_candidate_rank`
- `selection_rule_version`
- `selection_notes`

Minimum artifact and extraction fields:

- `raw_file_path`
- `raw_file_sha256`
- `raw_file_bytes`
- `text_file_path`
- `clean_text_sha256`
- `text_extraction_method`
- `extraction_status`
- `word_count`
- `section_count` if sectioning is implemented
- `table_text_handling`
- `extraction_quality_flags`

Minimum analysis fields:

- `taxonomy_version`
- `theme_categories`
- `theme_evidence_json`
- `tone_or_linguistic_metrics_json`
- `analyst_notes`

## Required Logs and Manifests

The pipeline should emit these audit artifacts:

- `target_company_years.csv`: exactly 450 rows for the 50 companies and 2016-2024.
- `cik_resolution.csv`: one row per input ticker with CIK, SEC name, match method, and review flag.
- `submissions_query_log.csv`: one row per CIK metadata request with URL, timestamp, HTTP status, retry count, and result count.
- `filing_candidates.csv`: all candidate filings returned for each company-year before selection.
- `selected_filings.csv`: the chosen filing per company-year plus selection rationale.
- `download_log.csv`: URL, local path, bytes, hash, HTTP status, and retry/error metadata.
- `extraction_log.csv`: parser used, input hash, output hash, text length, warnings, and quality flags.
- `coverage_report.json`: counts by status, sector, company, and year.
- `requirement_audit.json`: machine-checkable pass/fail checks for target grid, required columns, non-usable gap reasons, hashes, and artifact existence.
- `manual_review_queue.csv`: rows needing human review, especially CIK ambiguity, multiple DEF 14A candidates, very low word count, or extraction warnings.

These outputs are part of evidence, not just debugging convenience.

## Definition of Real Collection Success

A company-year should count as successfully collected only if all of the following are true:

1. The row maps to the correct company and CIK with no unresolved identity warning.
2. A filing with `form_type == "DEF 14A"` exists for the target year under the selected year rule.
3. The selected filing has a valid SEC accession number and filing detail URL.
4. The primary filing document was downloaded from `sec.gov/Archives`.
5. The downloaded artifact exists locally, has nonzero bytes, and has a recorded SHA-256 hash.
6. The parser produced cleaned text with a recorded hash.
7. The cleaned text passes minimum quality thresholds, such as a reasonable word count and expected proxy-related terms.
8. The row records source URL, filing date, accession number, extraction method, and status.
9. Any warnings are retained rather than overwritten.

Suggested minimum quality thresholds for initial smoke validation:

- `raw_file_bytes > 10_000`
- `word_count > 2_000`
- cleaned text contains at least two proxy anchors such as "proxy statement", "annual meeting", "board of directors", "executive compensation", or "shareholders"
- no unresolved `download_failed`, `extraction_failed`, or `no_cik_match` status

Thresholds should be used as flags, not silent exclusions.

## Smoke and Validation Outputs Beyond Tests

Unit tests can prove parser functions and selection logic on fixtures. They cannot prove that real SEC data was collected. The following outputs should be required before claiming Part 2 data collection success:

- A 450-row coverage table with every company-year represented.
- A status summary by year and sector.
- A list of observed CIKs and SEC registrant names for all 50 companies.
- A candidate filing count distribution, including rows with zero or multiple candidates.
- A sample manifest of at least one successfully downloaded filing per sector and per year where available.
- A checksum manifest proving raw and cleaned artifacts exist.
- A top-level coverage report showing usable rows, non-usable rows, and gap reasons.
- A manual review queue for ambiguous or suspicious rows.
- A text-length distribution with outliers flagged.
- A small excerpt QA file containing filing metadata plus first/representative cleaned-text snippets for a stratified sample.
- A theme-evidence file similar to Part 1's evidence contract: no positive theme without exact matched phrases or excerpts.
- A reproducibility report with command run, code version or git commit, pipeline configuration, and timestamp.

Recommended smoke command acceptance:

- A smoke run on 2 companies across 2 years should create target rows, resolve CIKs, retrieve SEC metadata, download at least one raw filing if available, extract text, compute hashes, and write coverage/requirement audit outputs.
- The smoke output should include at least one known high-coverage company such as Microsoft, Apple, JPMorgan Chase, or ExxonMobil, so a zero-success smoke run cannot pass unnoticed.

## Compatibility With Part 1 Taxonomy

Part 1 uses an auditable keyword-and-phrase taxonomy with source excerpts for every positive assignment. Part 2 should reuse this evidence standard where possible:

- Store the same `taxonomy_version` style for Part 2.
- Preserve exact matched phrases and literal source excerpts for positive assignments.
- Use `null` for missing or unusable observations, not an empty theme list.
- Keep theme absence separate from document absence and parser failure.
- Report normalized rates per 100 words to avoid document-length artifacts.

Part 2 may need supplemental proxy-specific metrics because DEF 14A naturally emphasizes governance and compensation. Recommended additions:

- board independence and accountability language
- executive compensation and incentive language
- shareholder rights and voting language
- human capital and workforce language
- board diversity language
- sustainability or climate governance language
- risk oversight language

If these are added, they should be versioned separately from the Part 1 taxonomy or clearly documented as a Part 2 extension.

## Recommended Acceptance Criteria

Part 2 should be accepted as methodologically complete when:

1. The chosen document type is explicitly `DEF 14A proxy statement`, with construct-validity limitations documented.
2. The fixed 50-company sample from `part1_stated_values/config/companies.csv` is used without silent substitutions.
3. The target grid contains exactly 450 company-year rows for 2016-2024.
4. Every target row has a controlled collection status.
5. Every non-usable row has a structured `gap_reason`.
6. Every usable row has CIK, accession number, filing date, source URL, local raw artifact path, raw hash, clean text hash, word count, and extraction status.
7. Filing selection is deterministic and versioned.
8. Candidate filings are retained before filtering/selection.
9. SEC request logs include timestamps, URLs, HTTP statuses, retry counts, and user-agent/config metadata.
10. Download and extraction logs can be joined back to final rows.
11. The pipeline is resumable and does not require paid services or manual browser collection.
12. Positive theme assignments include phrase/excerpt evidence.
13. Missing documents, failed downloads, failed extraction, and thematic absence are represented as distinct states.
14. Coverage and quality reports are generated and checked before analysis.
15. A smoke run against real SEC data produces raw artifacts, text artifacts, and a requirement audit.
16. README/codebook documents every final dataset column and why it exists.

## Current Audit Conclusion

The Part 2 SEC DEF 14A approach is feasible and defensible, but only if the implementation treats collection evidence as a first-class output. The most important audit requirement is not maximum coverage; it is a complete, reproducible status ledger that proves what was attempted, what succeeded, what failed, and why.

The pipeline should not claim data acquisition success from tests alone. It should require real SEC-derived artifacts, accession-level provenance, hashes, extraction metrics, and human-review queues before downstream text mining or authenticity scoring uses the data.
