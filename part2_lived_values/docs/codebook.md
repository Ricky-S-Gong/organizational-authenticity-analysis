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
