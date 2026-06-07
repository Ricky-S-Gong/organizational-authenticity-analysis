# Part 2 Summary

Part 2 uses SEC `DEF 14A` proxy statements as the single lived-values disclosure type. The full run
collected 434 of 450 company-years (96.44%).
The 16 missing rows are documented and not imputed.

The baseline text-mining analysis uses deterministic, free, reproducible methods only: Part
1-compatible theme matching, phrase evidence, normalized rates per 10,000 words, and descriptive
linguistic metrics. The enhanced analysis adds separate open-source modeling outputs with
TF-IDF/NMF topics, `sentence-transformers/all-MiniLM-L6-v2` embeddings, spaCy features, and a
sampled local `google/flan-t5-small` annotation pass. The enhanced outputs are exploratory aids and
are not mixed into the phrase-evidence baseline.

The main result is that proxy disclosures are dominated by shareholder/performance language
(37.8 matches per 10,000 words),
but employee/workplace, DEI, and leadership/accountability language are also pervasive. Cross-sector
variation is meaningful: technology is strongest on DEI, energy is unusually high on
environment/sustainability, and financials/healthcare/consumer discretionary remain more
shareholder/performance heavy.

The 2020-2021 event window shows descriptive increases in DEI, employee/workplace, sustainability,
and health/safety language relative to pre-2020 levels. These shifts are plausible in light of
COVID-era workforce concerns, post-2020 DEI attention, and ESG governance pressure, but they are
not causal estimates.

Saved figures:

- `../outputs/text_mining/figures/theme_over_time.png`
- `../outputs/text_mining/figures/sector_theme_heatmap.png`
- `../outputs/text_mining/figures/event_window_theme_change.png`

Saved Markdown and LaTeX tables live in `../outputs/text_mining/tables/`.

Enhanced model outputs live in `../outputs/text_mining/enhanced/`, with parameters and stage
statuses in `enhanced_text_mining_summary.json` and the live JSONL log in
`../data/interim/enhanced_text_mining_run_log.jsonl`. The strongest model-based finding is that
NMF mostly recovers proxy-structure themes (shareholders, stockholder meetings, forward-looking
statements, annual general meeting mechanics) rather than a clean latent values taxonomy. This is
important substantively: in `DEF 14A`, lived-values language is embedded inside governance
machinery, so exact evidence review remains necessary.
