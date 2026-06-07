# Enhanced Part 2 Text Mining Analysis

## Method

This enhancement adds exploratory open-source NLP/modeling layers on top of the existing
deterministic Part 2 baseline. It uses TF-IDF + NMF topic modeling, sentence-transformer
embeddings, a spaCy statistical pipeline, and an optional local open-source LLM annotation pass.
These outputs are interpretive aids, not replacements for the exact phrase evidence used in the
baseline.

The run covers 434 collected company-years and records all parameters in
`../outputs/text_mining/enhanced/enhanced_text_mining_summary.json`. The JSONL progress log is
`../data/interim/enhanced_text_mining_run_log.jsonl`.

## TF-IDF + NMF

Status: `completed`. The NMF layer estimates latent disclosure topics from
the representative text window of each proxy statement with seed `42`.

- nmf_topic_2: strategy / shareholders / company / billion (total score 30.60)
- nmf_topic_1: stockholders / awards / 2016 / 2017 (total score 19.17)
- nmf_topic_4: 2023 / 2022 / shareholders / shareholder (total score 18.03)
- nmf_topic_3: stockholders / meeting stockholders / stockholder / proxy materials (total score 16.28)
- nmf_topic_7: forward looking / looking statements / statements / looking (total score 14.05)

These topics should be read as recurring language bundles in the proxy corpus. They are useful for
discovering patterns that the fixed theme dictionary may miss, but topic labels remain researcher
interpretations of top terms.

## Sentence Embeddings

Status: `completed`. The embedding layer uses
`sentence-transformers/all-MiniLM-L6-v2` and writes both a manifest and
adjacent-year semantic-shift table. This layer is best used for finding filings whose overall
semantic profile changed sharply across adjacent years.

## spaCy Pipeline

Status: `completed`. The spaCy layer records part-of-speech and named-entity
features with `en_core_web_sm`. Because proxy
statements contain legal boilerplate and tables, entity counts are descriptive features rather than
ground-truth entity extraction.

## Local LLM Annotation

Status: `completed`. The local LLM layer is intentionally optional and sampled.
When enabled, every annotation records model name, prompt hash, excerpt hash, seed, temperature,
response hash, `annotation_quality_flag`, and `needs_human_review` status. In the current run,
the small local FLAN-T5 model generated a mix of one candidate interpretive signal and several
empty, fragmentary, or boilerplate-like annotations. That result is substantively useful as a
negative audit finding: for this proxy corpus, the local LLM layer is not reliable enough to carry
the analysis and should remain a low-weight qualitative aid.

## Reproducibility Notes

All stochastic stages use seed `42`. Model downloads are free/open-source but still
depend on package/model availability. For audit, rerun from the same `uv.lock`, same input dataset
hash `1422d669d575a15ae005ef4fb9664f5f7d240c4345aac81a37bc7f79e02e42ee`, and the parameters in the enhanced summary JSON.
