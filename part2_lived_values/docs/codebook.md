# Part 2 Data Codebook

Git-friendly dataset: `outputs/part2_company_year_compact.csv`

Full local dataset: `outputs/part2_company_year.csv`

The full local dataset includes `page_text_clean` and is intentionally ignored by Git because it
contains the extracted text for 434 proxy statements. The compact dataset keeps all source,
provenance, status, hash, theme, and metric fields while omitting only `page_text_clean`.

## Script Task Map

The Part 2 code is organized around a few large reproducible tasks. Command-line modules execute
the workflow, while support modules hold reusable collection, extraction, and analysis logic.

<table>
  <thead>
    <tr>
      <th>Large task</th>
      <th>Script/module</th>
      <th>Executes which task</th>
      <th>Function of the script/module</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Target setup</td>
      <td><code>src/org_auth_part2/targets.py</code></td>
      <td>Builds <code>config/company_year_targets.csv</code>.</td>
      <td>Loads the fixed Part 1 company list and expands it into the 50-company by 2016-2024 target grid.</td>
    </tr>
    <tr>
      <td rowspan="4">SEC collection</td>
      <td><code>src/org_auth_part2/run.py</code></td>
      <td>Runs the full DEF 14A collection pipeline.</td>
      <td>Resolves tickers to CIKs, selects annual proxy filings, downloads raw SEC artifacts, extracts clean text, writes hashes, logs progress, and exports full/compact datasets.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part2/edgar.py</code></td>
      <td>Supports SEC metadata and filing access.</td>
      <td>Wraps EDGAR requests, ticker-CIK lookup, submissions pagination, archive URL construction, and deterministic DEF 14A filing selection.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part2/extract.py</code></td>
      <td>Supports text extraction quality control.</td>
      <td>Extracts visible text from SEC HTML/plain-text filings and assigns extraction quality labels such as <code>usable</code> or <code>insufficient_text</code>.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part2/models.py</code></td>
      <td>Supports typed collection records.</td>
      <td>Defines immutable company, company-year, filing metadata, and collection-result records shared across scripts.</td>
    </tr>
    <tr>
      <td>Monitoring</td>
      <td><code>src/org_auth_part2/status.py</code></td>
      <td>Summarizes live collection progress.</td>
      <td>Reads the JSONL progress log and latest state file to report event counts, most recent event, and run position.</td>
    </tr>
    <tr>
      <td>Validation</td>
      <td><code>src/org_auth_part2/validate.py</code></td>
      <td>Validates generated Part 2 outputs.</td>
      <td>Checks dataset existence, row counts, successful source/text evidence, coverage/audit JSONs, and enhanced-output join keys.</td>
    </tr>
    <tr>
      <td rowspan="2">Baseline text mining</td>
      <td><code>src/org_auth_part2/analyze.py</code></td>
      <td>Supports deterministic theme and linguistic metrics.</td>
      <td>Applies the Part 1-compatible keyword taxonomy, stores literal phrase evidence, and computes lexical language/tone metrics.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part2/text_mining.py</code></td>
      <td>Runs deterministic analysis outputs.</td>
      <td>Aggregates theme rates, language/tone summaries, sector variation, adjacent-year shifts, event-window summaries, missingness tables, and baseline analysis docs.</td>
    </tr>
    <tr>
      <td rowspan="2">Baseline presentation</td>
      <td><code>src/org_auth_part2/figures.py</code></td>
      <td>Generates baseline figures.</td>
      <td>Creates SVG figures and optional PNG versions for theme trends, sector heatmaps, event-window changes, language/tone trends, and document-length context.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part2/presentation.py</code></td>
      <td>Generates tables and narrative docs.</td>
      <td>Writes Markdown/LaTeX tables and refreshes <code>docs/text_mining_analysis.md</code> and <code>docs/summary.md</code> from saved analysis outputs.</td>
    </tr>
    <tr>
      <td rowspan="2">Enhanced model checks</td>
      <td><code>src/org_auth_part2/enhanced_text_mining.py</code></td>
      <td>Runs open-source exploratory model checks.</td>
      <td>Runs TF-IDF/NMF topics, MiniLM embeddings, spaCy features, and optional local FLAN-T5 annotations with logged seeds, hashes, versions, and output paths.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part2/enhanced_presentation.py</code></td>
      <td>Presents enhanced model-check outputs.</td>
      <td>Builds enhanced Markdown/LaTeX tables, PNG figures, and merges the enhanced-check section into the main analysis document.</td>
    </tr>
    <tr>
      <td>Quality assurance</td>
      <td><code>tests/</code></td>
      <td>Runs Part 2 unit tests.</td>
      <td>Tests target-grid construction, SEC selection logic, extraction, deterministic analysis, figures, enhanced checks, status, and validation.</td>
    </tr>
  </tbody>
</table>

## Dataset Columns

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
