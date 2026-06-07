# Part 2 Summary

## Scope

Part 2 collects and analyzes lived-values disclosures for the same 50 companies and 2016-2024
company-year window used in Part 1. The selected disclosure type is SEC `DEF 14A` proxy
statements.

## Coverage

The collection target is a balanced 50-company by 9-year panel, for 450 target company-years. For
each company-year, the pipeline attempted to collect one calendar-year SEC `DEF 14A` proxy
statement from EDGAR.

| Collection status | Count | Share |
| --- | --- | --- |
| Collected | 434 | 96.44% |
| Missing | 16 | 3.56% |

The successful rows contain SEC filing metadata, accession numbers, archive URLs, raw-content
hashes, clean-text hashes, extracted proxy text, word/sentence counts, deterministic theme
evidence, and linguistic metrics. The collection source is the free SEC EDGAR submissions API and
Archives. There were no download or extraction failures among selected filings, and no rows remain
pending manual review.

Coverage by sector is:

| Sector | Collected | Missing |
| --- | --- | --- |
| Consumer Discretionary | 88 | 2 |
| Energy | 89 | 1 |
| Financials | 81 | 9 |
| Healthcare | 90 | 0 |
| Technology | 86 | 4 |

All 16 missing rows have the same structured gap reason:
`no_def14a_filing_for_calendar_year`. The missing company-years are Apple 2018; Broadcom
2016-2018; BlackRock 2016-2024; McDonald's 2022; Starbucks 2024; and ExxonMobil 2021. Missing
rows are retained with these gap reasons and are not imputed or treated as zero disclosure.

## Method

The pipeline resolves tickers to SEC CIKs, retrieves company submissions metadata, selects the
calendar-year `DEF 14A` filing, downloads the primary filing document, extracts clean text, and
records source metadata and SHA256 hashes. The final compact dataset keeps company-year status,
SEC filing identifiers, source URLs, text metrics, theme categories, phrase evidence, and
linguistic metrics.

The baseline analysis uses a deterministic Part 1-compatible keyword taxonomy and normalizes theme
matches per 10,000 words. Language and tone are measured with auditable lexical indicators,
including collective voice, commitment terms, action/evidence terms, stakeholder orientation,
sentence length, and quantified claims. An enhanced exploratory layer adds TF-IDF/NMF topics,
MiniLM embeddings, spaCy features, and sampled local FLAN-T5 annotations, but these model-based
outputs are kept in separate audit files while their interpretation is merged into the main
text-mining analysis report.

## Findings

Proxy disclosures are dominated by shareholder and performance language, which is expected for
shareholder-facing governance documents. Employee/workplace, diversity/equity/inclusion, and
leadership/accountability language are also consistently present across the collected filings.

The language-and-tone analysis adds a distinct finding beyond topic prevalence. Collective voice
(`we/our/us`) increases from 1.212 to 1.681 markers per 100 words,
and stakeholder-oriented language remains higher in 2024 than in 2016 after peaking in 2021. By
contrast, commitment markers decline and action/evidence markers remain low. This suggests that
proxy disclosures become more stakeholder-facing and organizational in voice, but not more
narratively action-heavy.

The external-event analysis is descriptive rather than causal. The 2020-2021 window shows
increases in DEI, employee/workplace, sustainability, and health/safety language relative to the
pre-2020 period. These shifts appear to coincide with COVID-era workforce concerns, post-2020 DEI
attention, and ESG governance pressure. The post-2021 sustainability rate remains especially
elevated, which is consistent with continued investor attention to ESG governance.

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
