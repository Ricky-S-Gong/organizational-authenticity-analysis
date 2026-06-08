# Part 3 Codebook

## Script Task Map

The Part 3 code is organized around a few large reproducible tasks. Command-line modules execute
the workflow, while support modules hold reusable scoring, semantic-similarity, summary, figure,
and validation logic.

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
      <td>Shared configuration</td>
      <td><code>src/org_auth_part3/constants.py</code></td>
      <td>Defines the Part 3 file contract.</td>
      <td>Stores input paths, output paths, required final-index columns, the shared taxonomy version, theme labels, and semantic-embedding configuration used across Part 3 modules.</td>
    </tr>
    <tr>
      <td rowspan="2">Index construction</td>
      <td><code>src/org_auth_part3/index.py</code></td>
      <td>Builds <code>outputs/part3_authenticity_index.csv</code>.</td>
      <td>Merges the finalized Part 1 and Part 2 company-year panels, parses shared taxonomy evidence into 12-theme vectors, applies score-status rules, computes the primary alignment index and theme-vector robustness scores, adds source provenance, and appends semantic/context fields.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part3/semantic.py</code></td>
      <td>Builds <code>outputs/semantic_similarity.csv</code>.</td>
      <td>Reads comparable Part 1 and Part 2 clean-text windows, classifies semantic-comparison eligibility, embeds available text with <code>sentence-transformers/all-MiniLM-L6-v2</code>, and writes supplementary whole-text similarity scores.</td>
    </tr>
    <tr>
      <td>Summary tables</td>
      <td><code>src/org_auth_part3/summaries.py</code></td>
      <td>Builds distribution, sector, year, company, and sensitivity summaries.</td>
      <td>Aggregates scored rows into <code>distribution_summary.csv</code>, <code>sector_summary.csv</code>, <code>year_summary.csv</code>, <code>company_summary.csv</code>, and <code>sensitivity_summary.csv</code>, including robustness correlations and missingness counts.</td>
    </tr>
    <tr>
      <td>Validity and audit</td>
      <td><code>src/org_auth_part3/validity.py</code></td>
      <td>Builds <code>outputs/validity_case_audit.csv</code>.</td>
      <td>Selects high- and low-alignment scored company-years for face-validity review, formats top-theme and theme-gap evidence, and retains source URLs for human inspection.</td>
    </tr>
    <tr>
      <td>Figures</td>
      <td><code>src/org_auth_part3/figures.py</code></td>
      <td>Builds PNG and SVG figures under <code>outputs/figures/</code>.</td>
      <td>Creates the primary score distribution, sector and year plots, keyword/semantic/hybrid comparison plots, and keyword-semantic quadrant scatter plot used in the written summary.</td>
    </tr>
    <tr>
      <td>Generated presentation tables</td>
      <td><code>src/org_auth_part3/presentation.py</code></td>
      <td>Builds <code>docs/results_snapshot.md</code>.</td>
      <td>Converts saved CSV summaries into Markdown tables, including keyword/semantic/hybrid summaries and representative quadrant cases, so the documentation stays synchronized with generated outputs.</td>
    </tr>
    <tr>
      <td>Validation</td>
      <td><code>src/org_auth_part3/validate.py</code></td>
      <td>Builds <code>outputs/requirement_audit.json</code>.</td>
      <td>Checks the final panel row count, unique keys, required columns, score completeness for scored rows, source traceability, semantic-status fields, taxonomy version, and existence of supporting outputs.</td>
    </tr>
    <tr>
      <td>Quality assurance</td>
      <td><code>tests/</code></td>
      <td>Runs Part 3 unit tests.</td>
      <td>Tests theme-evidence parsing, vector normalization, scoring bounds, score-status rules, semantic helper behavior, and validation audit expectations.</td>
    </tr>
  </tbody>
</table>

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
