# Part 2 Methodology

## Document Type

The selected document type is SEC `DEF 14A` proxy statements.

This choice prioritizes reproducibility, coverage, and auditability. EDGAR filings are official
public records, available without paid APIs, and expose stable CIK, accession, filing date, and
archive URL metadata. The tradeoff is construct validity: proxy statements reveal disclosed
governance, compensation, voting, and board priorities. They do not directly prove lived behavior.

## Collection Source

The pipeline uses free SEC endpoints:

- ticker to CIK map: `https://www.sec.gov/files/company_tickers.json`
- submissions history: `https://data.sec.gov/submissions/CIK##########.json`
- primary documents: `https://www.sec.gov/Archives/edgar/data/...`

The runner uses a declared User-Agent and configurable request delay to respect SEC fair-access
expectations.

## Selection Rule

For each company-year, the pipeline selects the first calendar-year `DEF 14A` filing in the SEC
submissions history. `DEFA14A` supplemental filings are not used by default because the assignment
asks for one comparable document type.

## Text Extraction

Downloaded primary documents are stored under `data/raw/filings/`. Clean text is extracted from
visible HTML text and stored under `data/processed/text/`. Every raw and clean artifact receives a
SHA256 hash.

Extraction quality is coded as:

- `usable`: at least 1,000 words and not obviously index-only.
- `insufficient_text`: non-empty text below the threshold.
- `possibly_index_only`: table-of-contents-heavy text below the stricter screen.
- `empty`: no extractable words.

## Analysis

Part 2 applies the same fixed theme IDs used in Part 1 taxonomy version
`1.0.0-keyword-baseline`, plus deterministic linguistic metrics. This creates a shared
representation for Part 3 alignment analysis.

An enhanced analysis module is also provided as a separate exploratory layer. It uses free,
open-source tooling managed by the shared root `uv` environment:

- scikit-learn TF-IDF + NMF topic modeling with fixed `random_state=42`.
- `sentence-transformers/all-MiniLM-L6-v2` embeddings with normalized document vectors.
- spaCy `en_core_web_sm` statistical features.
- sampled local `google/flan-t5-small` annotations with seed, temperature, prompt hash, excerpt
  hash, response hash, and quality flags.

These model-based outputs are deliberately stored under `outputs/text_mining/enhanced/` and are
not used as substitutes for the deterministic phrase-evidence baseline. The local LLM annotations
are marked `needs_human_review`; in this run, most were fragmentary or boilerplate-like, so they
are retained as an audit trail rather than used as substantive evidence.

## Audit Strategy

Automated collection is the production path. Human work is reserved for audit:

- review non-collected and low-quality rows
- inspect a sample of successful rows
- verify that selected documents are true proxy statements
- avoid treating disclosure language as direct behavioral evidence
