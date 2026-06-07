# Part 2 Text Mining Analysis

## Research Design and Method

Part 2 analyzes SEC `DEF 14A` proxy statements as a free, official, and reproducible disclosure
source. The full run covers 434 of 450 company-years
(96.44%). The remaining 16 rows are retained as
documented gaps and are not imputed.

The analysis uses deterministic text mining only: Part 1-compatible theme matching, literal phrase
evidence, document-length-normalized rates, and descriptive linguistic metrics. I did not use a
paid API, closed model, or external LLM. This keeps the analysis auditable and appropriate for a
small RA interview assignment.

## 1. Overall Disclosure Priorities

![Theme emphasis over time](../outputs/text_mining/figures/theme_over_time.png)

| Theme | Mean matches / 10k words | Presence |
| --- | --- | --- |
| Shareholders and performance | 37.78 | 100.0% |
| Employees and workplace | 28.11 | 100.0% |
| Diversity, equity, and inclusion | 25.82 | 100.0% |
| Leadership and accountability | 24.87 | 100.0% |
| Customers and service | 16.79 | 99.8% |
| Environment and sustainability | 13.72 | 98.8% |
| Health, safety, and wellbeing | 10.50 | 100.0% |
| Integrity and ethics | 6.96 | 100.0% |

The strongest overall signal is not surprising: proxy statements are shareholder-facing governance
documents, so `Shareholders and performance` is the top normalized theme at
37.8 matches per 10,000 words.
What is more substantively useful is that workforce and DEI language are also pervasive. `Employees
and workplace` and `Diversity, equity, and inclusion` appear in every collected company-year and
rank second and third by normalized intensity. This suggests that by 2016-2024, proxy statements
were no longer only compensation and voting documents; they had become a venue for communicating
human-capital and governance identity claims.

## 2. Cross-Sector Comparison

![Sector theme heatmap](../outputs/text_mining/figures/sector_theme_heatmap.png)

| Sector | Top normalized themes |
| --- | --- |
| Consumer Discretionary | Shareholders and performance (53.0); Leadership and accountability (27.8); Diversity, equity, and inclusion (25.2) |
| Energy | Employees and workplace (31.3); Shareholders and performance (25.7); Environment and sustainability (23.8) |
| Financials | Shareholders and performance (43.9); Diversity, equity, and inclusion (30.8); Employees and workplace (30.1) |
| Healthcare | Shareholders and performance (47.3); Employees and workplace (28.7); Diversity, equity, and inclusion (23.1) |
| Technology | Diversity, equity, and inclusion (33.3); Employees and workplace (28.2); Leadership and accountability (25.1) |

The sector comparison shows both document-type regularity and meaningful heterogeneity.
Consumer discretionary, healthcare, and financial firms are especially shareholder/performance
heavy. Technology is distinctive: its highest normalized theme is DEI at
33.3 matches per 10,000 words. Energy is also distinctive: environment
and sustainability reaches 23.8 matches per 10,000 words, much
higher than the overall mean, but employee/workplace language remains the sector's top category.
These differences are useful for Part 3 because an alignment measure should not treat all sectors
as having the same expected disclosure vocabulary.

## 3. Time and External-Event Window

![Event-window theme change](../outputs/text_mining/figures/event_window_theme_change.png)

| Theme | Pre-2020 | 2020-2021 | Post-2021 | Window - pre |
| --- | --- | --- | --- | --- |
| Diversity, equity, and inclusion | 21.54 | 28.30 | 29.83 | 6.76 |
| Employees and workplace | 25.15 | 31.40 | 29.83 | 6.25 |
| Environment and sustainability | 8.06 | 12.99 | 21.71 | 4.94 |
| Shareholders and performance | 35.21 | 39.34 | 40.13 | 4.13 |
| Health, safety, and wellbeing | 8.18 | 11.26 | 13.08 | 3.08 |
| Social impact and community | 2.10 | 4.97 | 4.67 | 2.87 |
| Customers and service | 15.63 | 17.61 | 17.79 | 1.98 |
| Leadership and accountability | 23.59 | 25.28 | 26.28 | 1.68 |

The 2020-2021 window shows the clearest descriptive increase in themes tied to workforce, DEI,
sustainability, and stakeholder concern. DEI rises by 6.76 matches per 10,000 words relative to the
pre-2020 period; employee/workplace language rises by 6.25; and environment/sustainability rises by
4.94. These changes are consistent with the COVID-era workforce shock, the post-2020 DEI disclosure
cycle, and growing investor attention to ESG governance. They should not be interpreted as causal
effects: proxy templates, regulatory expectations, and investor norms changed at the same time.

## 4. Within-Company Shifts

| Ticker | Years | Theme | Change / 10k words |
| --- | --- | --- | --- |
| BAC | 2019-2020 | Shareholders and performance | 64.94 |
| BRK.B | 2018-2019 | Environment and sustainability | -49.72 |
| AAPL | 2022-2023 | Shareholders and performance | 45.02 |
| NKE | 2020-2021 | Diversity, equity, and inclusion | 44.76 |
| TMO | 2018-2019 | Shareholders and performance | 44.33 |
| META | 2020-2021 | Shareholders and performance | 40.63 |
| NKE | 2021-2022 | Diversity, equity, and inclusion | -40.12 |
| HAL | 2018-2019 | Shareholders and performance | 39.19 |
| SLB | 2022-2023 | Shareholders and performance | 36.34 |
| VLO | 2021-2022 | Environment and sustainability | 35.26 |

The largest adjacent-year movements should be treated as audit targets rather than final causal
claims. For example, BAC's shareholder/performance language jumps sharply from 2019 to 2020, while
Nike's DEI language rises sharply from 2020 to 2021 and then partially reverses in 2022. These are
exactly the kinds of cases where a researcher should inspect the underlying proxy sections before
making a substantive claim.

A short excerpt audit confirms why this caution matters. BAC's 2019-2020 increase appears driven
substantially by shareholder meeting mechanics, shareholder proposals, proxy access, voting
instructions, and engagement language. By contrast, Nike's 2020-2021 DEI increase is more
substantively connected to diversity/inclusion reporting and board diversity language, though some
matches still come from proposal mechanics. The audit is saved in
`docs/top_shift_excerpt_audit.md` and `outputs/text_mining/top_shift_excerpt_audit.csv`.

## 5. Coverage and Missingness

| Ticker | Sector | Missing years | Count |
| --- | --- | --- | --- |
| AAPL | Technology | 2018 | 1 |
| AVGO | Technology | 2016,2017,2018 | 3 |
| BLK | Financials | 2016,2017,2018,2019,2020,2021,2022,2023,2024 | 9 |
| MCD | Consumer Discretionary | 2022 | 1 |
| SBUX | Consumer Discretionary | 2024 | 1 |
| XOM | Energy | 2021 | 1 |

Coverage is high enough for descriptive text mining, but missingness is not random enough to ignore.
BlackRock accounts for nine of the sixteen gaps, and Broadcom accounts for three. For Part 3, these
company-years should remain missing rather than being assigned zero disclosure emphasis or filled
with sector means.

## 6. Enhanced Model-Based Checks

The enhanced layer adds TF-IDF/NMF, sentence-transformer embeddings, spaCy features, and a sampled
local FLAN-T5 annotation pass. These outputs are saved separately in
`outputs/text_mining/enhanced/` with full parameters in
`enhanced_text_mining_summary.json`.

![NMF topic prevalence](../outputs/text_mining/enhanced/figures/enhanced_nmf_topic_scores.png)

| Topic | Corpus score | Top terms |
| --- | --- | --- |
| T2 | 30.60 | strategy; shareholders; company; billion; commitment; new; strong |
| T1 | 19.17 | stockholders; awards; 2016; 2017; proposal; meeting stockholders; stockholder |
| T4 | 18.03 | 2023; 2022; shareholders; shareholder; virtual; proposal; shareholder proposal |
| T3 | 16.28 | stockholders; meeting stockholders; stockholder; proxy materials; california; internet; stockholder proposal |
| T7 | 14.05 | forward looking; looking statements; statements; looking; forward; differ; actual results |
| T6 | 12.07 | abbott; abbvie; item proxy; abbott laboratories; laboratories; vote approval; item |
| T8 | 10.82 | annual general; general meeting; irish; medtronic; irish statutory; statutory financial; statutory |
| T5 | 7.87 | class stock; berkshire; berkshire hathaway; hathaway; omaha; nebraska; omaha nebraska |

The NMF results deepen the construct-validity reading rather than replacing the baseline. The
highest-scoring topic is not a pure value construct; it mixes strategy, shareholders, company, and
financial scale language. Other topics recover stockholder meeting mechanics, forward-looking
statement boilerplate, annual general meeting language, and company-specific templates. In other
words, in `DEF 14A`, lived-values language is embedded inside governance machinery rather than
presented as a clean cultural manifesto.

![Embedding semantic shifts](../outputs/text_mining/enhanced/figures/enhanced_embedding_shifts.png)

| Ticker | Years | Sector | Semantic distance | Cosine similarity |
| --- | --- | --- | --- | --- |
| TGT | 2021-2022 | Consumer Discretionary | 0.168 | 0.832 |
| VLO | 2021-2022 | Energy | 0.149 | 0.851 |
| JPM | 2022-2023 | Financials | 0.143 | 0.857 |
| XOM | 2020-2022 | Energy | 0.142 | 0.858 |
| TGT | 2022-2023 | Consumer Discretionary | 0.138 | 0.862 |
| SLB | 2022-2023 | Energy | 0.138 | 0.862 |
| JNJ | 2022-2023 | Healthcare | 0.135 | 0.865 |
| MPC | 2022-2023 | Energy | 0.135 | 0.865 |
| TMO | 2018-2019 | Healthcare | 0.135 | 0.865 |
| TMO | 2016-2017 | Healthcare | 0.133 | 0.867 |

The embedding layer is useful as a triage device. Large semantic distances point to filings whose
overall disclosure profile changed enough to justify qualitative review. Target 2021-2022, Valero
2021-2022, and JPMorgan 2022-2023 are the strongest model-identified candidates. These shifts are
not theme labels by themselves; they are pointers to company-year pairs where the surrounding
sections should be read manually.

![LLM annotation quality](../outputs/text_mining/enhanced/figures/enhanced_llm_quality.png)

| Quality flag | Count | Share |
| --- | --- | --- |
| candidate_interpretive_signal | 1 | 12.5% |
| low_boilerplate_like | 2 | 25.0% |
| low_empty_or_fragment | 5 | 62.5% |

The local LLM check is most useful as a negative audit result. Although the run is fully logged
with model name, seed, temperature, prompt hash, excerpt hash, and response hash, most sampled
annotations were empty, fragmentary, or boilerplate-like. Only one sampled output was flagged as a
candidate interpretive signal. This means the small local model should not carry any Part 2 claim;
it is retained as a transparent exploratory layer and a warning against over-reading cheap LLM
annotations in legal disclosure text.

## Interpretation

The core empirical takeaway is that proxy statements reveal a structured hierarchy of disclosed
priorities: shareholder/performance language remains dominant, but workforce, DEI, leadership, and
sustainability language are substantial and vary by sector and time. The construct-validity caveat
is central: this is evidence about disclosed priorities in legally structured corporate
communications, not direct evidence of lived organizational behavior.
