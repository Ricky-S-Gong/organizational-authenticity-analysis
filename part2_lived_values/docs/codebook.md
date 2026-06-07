# Part 2 Data Codebook

Git-friendly dataset: `outputs/part2_company_year_compact.csv`

Full local dataset: `outputs/part2_company_year.csv`

The full local dataset includes `page_text_clean` and is intentionally ignored by Git because it
contains the extracted text for 434 proxy statements. The compact dataset keeps all source,
provenance, status, hash, theme, and metric fields while omitting only `page_text_clean`.

| Column | Meaning |
| --- | --- |
| `ticker` | Company ticker from the fixed 50-company sample. |
| `company_name` | Company name from the fixed sample. |
| `sector` | Sector from the fixed sample. |
| `year` | Calendar filing year, 2016-2024. |
| `collection_status` | `collected`, `missing`, `failed`, or `needs_review`. |
| `gap_reason` | Controlled explanation when a row is not cleanly collected. |
| `cik` | SEC Central Index Key. |
| `form` | SEC form type, expected `DEF 14A` for collected rows. |
| `filing_date` | SEC filing date. |
| `report_date` | SEC report date when supplied. |
| `accession_number` | SEC accession number. |
| `primary_document` | SEC primary document filename. |
| `source_url` | SEC submissions JSON URL. |
| `sec_archive_url` | SEC archive URL for the primary document. |
| `raw_file_path` | Local path to the downloaded SEC filing artifact. |
| `raw_file_bytes` | Size of the downloaded SEC filing artifact in bytes. |
| `raw_content_sha256` | SHA256 hash of the downloaded filing artifact. |
| `clean_text_sha256` | SHA256 hash of the extracted clean text. |
| `text_path` | Local path to extracted clean text. |
| `page_text_clean` | Extracted proxy text. |
| `extraction_quality` | Extraction quality code. |
| `word_count` | Number of extracted words. |
| `sentence_count` | Number of extracted sentences. |
| `theme_categories` | JSON list of assigned Part 1-compatible theme IDs. |
| `theme_evidence` | JSON evidence records for assigned themes. |
| `linguistic_metrics` | JSON deterministic linguistic metrics. |
| `analyst_notes` | Notes and limitations for interpretation. |

## Theme Categories

`theme_categories` and `theme_evidence` use the deterministic taxonomy
`1.0.0-keyword-baseline`. A theme is assigned when at least one matching term or phrase appears in
the extracted proxy-statement text. Each positive assignment stores the matched phrases, match
count, and short evidence excerpts.

| Theme ID | Label |
| --- | --- |
| `customers_and_service` | Customers and service |
| `employees_and_workplace` | Employees and workplace |
| `innovation_and_excellence` | Innovation and excellence |
| `integrity_and_ethics` | Integrity and ethics |
| `diversity_equity_and_inclusion` | Diversity, equity, and inclusion |
| `social_impact_and_community` | Social impact and community |
| `environment_and_sustainability` | Environment and sustainability |
| `health_safety_and_wellbeing` | Health, safety, and wellbeing |
| `shareholders_and_performance` | Shareholders and performance |
| `leadership_and_accountability` | Leadership and accountability |
| `collaboration_and_partnership` | Collaboration and partnership |
| `purpose_and_identity` | Purpose and identity |

The full keyword/phrase list for these themes is documented in
`docs/methodology.md`.

## Linguistic Metrics

`linguistic_metrics` is a JSON object with deterministic counts and rates. It is designed to make
the language/tone analysis reproducible without a paid model or closed API.

| Metric family | JSON fields | Interpretation |
| --- | --- | --- |
| Document length | `word_count`; `sentence_count`; `average_sentence_length` | Basic document and sentence-length measures. |
| Quantification | `quantified_claim_count` | Count of numeric, percentage, or percent-style claims. |
| Collective voice | `first_person_plural_count`; `first_person_plural_rate_per_100_words` | `we`, `our`, `ours`, `us`. |
| Commitment | `commitment_count`; `commitment_rate_per_100_words` | `will`, `must`, `commit`, `committed`, `promise`, `pledge`. |
| Aspiration | `aspiration_count`; `aspiration_rate_per_100_words` | `aim`, `aims`, `aspire`, `seek`, `strive`, `hope`, `vision`. |
| Action/evidence | `action_or_evidence_count`; `action_or_evidence_rate_per_100_words` | `achieved`, `delivered`, `launched`, `reduced`, `increased`, `invest`, `invested`, `created`, `implemented`. |
| Stakeholder orientation | `stakeholder_count`; `stakeholder_rate_per_100_words` | `customer`, `customers`, `employee`, `employees`, `community`, `communities`, `supplier`, `suppliers`. |

These language/tone indicators are lexical proxies for disclosure style. They should be interpreted
as auditable signals of how proxy filings are written, not as sentiment scores or direct evidence
of organizational behavior.
