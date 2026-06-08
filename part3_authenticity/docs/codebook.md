# Part 3 Codebook

## Primary Dataset

Primary output: `outputs/part3_authenticity_index.csv`

The dataset contains all 450 required company-years. Rows without sufficient evidence for scoring
remain in the file with explicit `score_status` and `score_gap_reason`.

| Column | Meaning |
| --- | --- |
| `ticker` | Company ticker from the fixed 50-company sample. |
| `company_name` | Company name. |
| `sector` | Sector from the assignment sample. |
| `year` | Calendar year, 2016-2024. |
| `part1_observation_status` | Part 1 stated-values collection/extraction status. |
| `part1_gap_reason` | Part 1 gap reason when the stated-values row is not usable. |
| `part2_collection_status` | Part 2 proxy collection status. |
| `part2_gap_reason` | Part 2 gap reason when the proxy row is not collected. |
| `score_status` | Whether the Part 3 index is scored or why it is not scored. |
| `score_gap_reason` | Human-readable explanation for non-scored rows. |
| `authenticity_index` | Primary 0-100 theme-distribution alignment score. |
| `cosine_alignment` | Cosine similarity robustness score, scaled 0-100. |
| `l1_alignment` | Normalized L1 alignment robustness score, scaled 0-100. |
| `jaccard_theme_overlap` | Binary theme-set overlap, scaled 0-100. |
| `semantic_text_similarity` | Supplementary sentence-transformer cosine similarity between Part 1 and Part 2 representative text windows, scaled by 100. |
| `semantic_similarity_status` | Whether semantic similarity was computed or why it is unavailable. |
| `semantic_similarity_gap_reason` | Human-readable explanation when semantic similarity is unavailable. |
| `semantic_embedding_model` | Sentence-transformer model used for computed semantic similarity. |
| `sector_percentile` | Within-sector percentile rank for scored rows, 0-1. |
| `sector_z_score` | Within-sector standardized score for scored rows. |
| `stated_theme_total_matches` | Total deterministic theme matches in Part 1. |
| `disclosure_theme_total_matches` | Total deterministic theme matches in Part 2. |
| `stated_top_themes` | JSON list of the top three Part 1 themes by match count. |
| `disclosure_top_themes` | JSON list of the top three Part 2 themes by match count. |
| `theme_gap_summary` | JSON list of the five largest stated-minus-disclosure theme-share gaps. |
| `part1_clean_text_sha256` | Hash of the Part 1 cleaned stated-values text. |
| `part2_clean_text_sha256` | Hash of the Part 2 cleaned proxy text. |
| `part1_source_url` | Archived source URL used for the stated-values text. |
| `part2_sec_archive_url` | SEC archive URL for the selected proxy statement. |
| `taxonomy_version` | Shared taxonomy version used for scoring. |
| `part2_action_evidence_rate` | Part 2 action/evidence lexical rate per 100 words. |
| `part2_stakeholder_rate` | Part 2 stakeholder lexical rate per 100 words. |
| `part2_word_count` | Extracted proxy-statement word count. |

## Score Status Values

| Status | Meaning |
| --- | --- |
| `scored` | Part 1 and Part 2 are available and both contain nonzero theme evidence. |
| `missing_part1` | Part 1 stated-values observation is not usable. |
| `missing_part2` | Part 2 proxy disclosure is not collected. |
| `missing_both` | Neither source is available for scoring. |
| `insufficient_stated_theme_signal` | Part 1 is usable but has no deterministic theme matches. |
| `insufficient_disclosure_theme_signal` | Part 2 is collected but has no deterministic theme matches. |

## Semantic Similarity Status Values

| Status | Meaning |
| --- | --- |
| `computed` | Part 1 and Part 2 clean text are available and semantic similarity was computed. |
| `missing_part1_text` | Part 1 clean text is unavailable. |
| `missing_part2_text` | Part 2 clean text is unavailable. |
| `missing_both_text` | Neither side has clean text available for embedding. |
| `source_not_available` | One or both sources are unavailable, so semantic comparison is not applicable. |

## How to Read a Dataset Row

Start with `score_status`. Rows marked `scored` have a primary keyword-taxonomy index; rows with
another status should be interpreted through `score_gap_reason`, not as low-alignment cases. For
scored rows, read `authenticity_index` first, then inspect `stated_top_themes`,
`disclosure_top_themes`, and `theme_gap_summary` to understand which themes explain the score.
Use `semantic_text_similarity` as a supplementary whole-text check and `sector_percentile` or
`sector_z_score` for within-sector comparison.

The most useful row-level pattern is agreement or divergence across diagnostics:

- High keyword index and high semantic similarity: strong alignment across theme distribution and
  broad text meaning.
- High keyword index and lower semantic similarity: shared taxonomy themes but different document
  genre or rhetoric.
- Low keyword index and high semantic similarity: broad text similarity but weak values-theme
  overlap, possibly because the taxonomy misses synonyms or because the texts share generic
  corporate language.
- Low keyword index and low semantic similarity: strong audit signal that both thematic emphasis
  and whole-text meaning diverge.

## Supporting Outputs

| Output | Meaning |
| --- | --- |
| `outputs/distribution_summary.csv` | Overall score distribution and missingness. |
| `outputs/sector_summary.csv` | Sector-level score distribution and missingness. |
| `outputs/year_summary.csv` | Year-level score distribution and missingness. |
| `outputs/company_summary.csv` | Company-level average and median scores. |
| `outputs/validity_case_audit.csv` | Top 10 and bottom 10 scored company-years for face-validity review. |
| `outputs/semantic_similarity.csv` | Standalone semantic similarity robustness output for all 450 company-years. |
| `outputs/sensitivity_summary.csv` | Correlations with robustness scores and proxy word count. |
| `outputs/requirement_audit.json` | Machine-readable Part 3 validation audit. |
| `docs/case_audit_notes.md` | Qualitative review notes for high, low, and keyword-semantic divergence cases. |
| `outputs/figures/score_distribution.png` | Histogram of scored company-year authenticity scores. |
| `outputs/figures/sector_scores.png` | Mean score by sector. |
| `outputs/figures/year_scores.png` | Mean score by year. |
| `outputs/figures/metric_comparison_distributions.png` | Side-by-side keyword, semantic, and hybrid distribution comparison. |
| `outputs/figures/metric_comparison_sector.png` | Sector mean comparison across keyword, semantic, and hybrid standards. |
| `outputs/figures/metric_comparison_year.png` | Year mean comparison across keyword, semantic, and hybrid standards. |
| `outputs/figures/keyword_semantic_scatter.png` | Scatter plot showing keyword-semantic agreement and divergence cases. |
