# Part 2 Summary

## Scope

Part 2 collects and analyzes lived-values disclosures for the same 50 companies and 2016-2024
company-year window used in Part 1. The selected disclosure type is SEC `DEF 14A` proxy
statements.

## Coverage

- Target rows: 450
- Collected proxy statements: 434 of 450 (96.44%)
- Missing rows: 16
- Document type: SEC `DEF 14A`
- Source: SEC EDGAR submissions API and Archives

Missing rows are retained with structured gap reasons and are not imputed or treated as zero
disclosure.

## Method

The pipeline resolves tickers to SEC CIKs, retrieves company submissions metadata, selects the
calendar-year `DEF 14A` filing, downloads the primary filing document, extracts clean text, and
records source metadata and SHA256 hashes. The final compact dataset keeps company-year status,
SEC filing identifiers, source URLs, text metrics, theme categories, phrase evidence, and
linguistic metrics.

The baseline analysis uses a deterministic Part 1-compatible keyword taxonomy and normalizes theme
matches per 10,000 words. An enhanced exploratory layer adds TF-IDF/NMF topics, MiniLM embeddings,
spaCy features, and sampled local FLAN-T5 annotations, but these model-based outputs are kept
separate from the baseline phrase-evidence results.

## Findings

Proxy disclosures are dominated by shareholder and performance language, which is expected for
shareholder-facing governance documents. Employee/workplace, diversity/equity/inclusion, and
leadership/accountability language are also consistently present across the collected filings.

The 2020-2021 window shows descriptive increases in DEI, employee/workplace, sustainability, and
health/safety language relative to the pre-2020 period. These shifts are consistent with broader
COVID-era workforce concerns, post-2020 DEI attention, and ESG governance pressure, but they are
not causal estimates.

The enhanced model checks reinforce the construct-validity caveat: NMF mostly recovers
proxy-structure topics such as shareholder meetings, stockholder proposals, forward-looking
statements, and annual meeting mechanics. This suggests that lived-values language in `DEF 14A`
filings is embedded within governance machinery rather than presented as a clean cultural
manifesto.

## Limitation

`DEF 14A` filings are official, free, and highly auditable, but they are not direct observations of
organizational behavior. Part 2 should therefore be interpreted as evidence of disclosed
governance and human-capital priorities, not as proof of lived values. Missing company-years should
remain missing in downstream alignment analysis.
