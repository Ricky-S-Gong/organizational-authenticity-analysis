# Part 4 Codebook

## Primary Output

Primary dataset: `outputs/part4_genre_diagnostics.csv`

| Column | Meaning |
| --- | --- |
| `ticker` | Company ticker from the fixed 50-company sample. |
| `company_name` | Company name. |
| `sector` | Assignment sector. |
| `year` | Calendar year, 2016-2024. |
| `score_status` | Part 3 authenticity score status. |
| `genre_status` | Whether proxy-genre diagnostics were computed. |
| `genre_gap_reason` | Explanation when genre diagnostics are unavailable. |
| `authenticity_index` | Part 3 primary keyword-taxonomy alignment score. |
| `semantic_text_similarity` | Part 3 whole-text semantic similarity, scaled by 100. |
| `semantic_0_100` | Semantic similarity rescaled to a 0-100 comparison view. |
| `keyword_minus_semantic` | `authenticity_index - semantic_0_100`. |
| `part2_word_count` | Extracted proxy word count. |
| `shareholder_mechanics_count` | Raw count of shareholder-meeting mechanics phrases. |
| `shareholder_mechanics_rate` | Shareholder-mechanics count per 1,000 proxy words. |
| `governance_boilerplate_count` | Raw count of governance boilerplate phrases. |
| `governance_boilerplate_rate` | Governance-boilerplate count per 1,000 proxy words. |
| `legal_procedural_count` | Raw count of legal/procedural phrases. |
| `legal_procedural_rate` | Legal/procedural count per 1,000 proxy words. |
| `proxy_genre_pressure` | Average of z-scored genre-family rates. |
| `genre_pressure_tercile` | Low, medium, or high pressure among computed proxy rows. |
| `keyword_semantic_quadrant` | Median-split Part 3 keyword/semantic quadrant. |

## Section-Level Output

Section dataset: `outputs/section_diagnostics.csv`

| Column | Meaning |
| --- | --- |
| `section_status` | Whether a section row was parsed or why it is unavailable. |
| `section_family` | Heuristic proxy section family. |
| `section_title` | Detected section heading or fallback chunk label. |
| `section_word_count` | Number of words in the section span. |
| `section_share_of_proxy` | Section word share within the full proxy. |
| `section_genre_count` | Total genre-dictionary matches in the section. |
| `section_genre_rate` | Genre matches per 1,000 section words. |
| `dominant_theme_id` | Highest-count values theme in the section. |
| `total_theme_matches` | Total taxonomy-theme matches in the section. |
| `theme_*_count` | Per-theme deterministic match counts. |

## Theme-Level Semantic Output

Theme semantic dataset: `outputs/theme_level_semantic_similarity.csv`

| Column | Meaning |
| --- | --- |
| `theme_id` | Shared 12-theme taxonomy ID. |
| `theme_semantic_status` | Whether same-theme semantic comparison was computed. |
| `theme_semantic_similarity` | Same-theme Part 1/Part 2 local semantic similarity. |
| `theme_semantic_method` | Embedding model or deterministic fallback method. |
| `stated_excerpt_count` | Number of Part 1 evidence excerpts for the theme. |
| `disclosure_excerpt_count` | Number of Part 2 evidence excerpts for the theme. |
| `stated_theme_match_count` | Part 1 deterministic match count for the theme. |
| `disclosure_theme_match_count` | Part 2 deterministic match count for the theme. |
| `stated_theme_share` | Part 1 within-document theme share. |
| `disclosure_theme_share` | Part 2 within-document theme share. |
| `theme_share_gap_abs` | Absolute stated-vs-disclosure theme-share gap. |

## Supporting Outputs

| Output | Meaning |
| --- | --- |
| `outputs/genre_pressure_summary.csv` | Overall and tercile-level summary. |
| `outputs/genre_pressure_correlations.csv` | Correlations with key Part 3 diagnostics. |
| `outputs/quadrant_genre_summary.csv` | Genre pressure by keyword-semantic quadrant. |
| `outputs/case_audit_targets.csv` | Selected qualitative audit candidates. |
| `outputs/genre_pressure_regression.csv` | Descriptive fixed-effects regression coefficients. |
| `outputs/section_summary.csv` | Aggregate contribution by parsed section family. |
| `outputs/theme_level_semantic_summary.csv` | Aggregate same-theme semantic similarity by theme. |
| `outputs/requirement_audit.json` | Machine-readable structural validation. |
| `outputs/figures/genre_pressure_vs_authenticity.png` | Genre pressure/authenticity scatter. |
| `outputs/figures/genre_pressure_terciles.png` | Mean authenticity by genre-pressure tercile. |
| `outputs/figures/quadrant_genre_pressure.png` | Genre pressure by keyword-semantic quadrant. |
| `outputs/figures/section_authenticity_contribution.png` | Theme evidence by section family. |
| `outputs/figures/theme_level_semantic_similarity.png` | Same-theme semantic similarity by theme. |
| `outputs/figures/section_theme_heatmap.png` | Theme composition across section families. |
| `outputs/figures/section_theme_composition.png` | Section size versus values-theme density. |
| `outputs/figures/theme_semantic_gap_scatter.png` | Theme semantic/gap scatter. |

## Case-Audit Output

Case-audit dataset: `outputs/case_audit_targets.csv`

| Column | Meaning |
| --- | --- |
| `audit_bucket` | OAI/SS bucket used for qualitative case review. |
| `ticker`, `company_name`, `sector`, `year` | Company-year identifiers. |
| `authenticity_index` | Primary Organizational Authenticity Index (OAI). |
| `semantic_0_100` | Whole-text semantic similarity (SS), rescaled to 0-100. |
| `keyword_minus_semantic` | OAI minus SS; negative values flag semantic/theme divergence. |
| `proxy_genre_pressure` | Auxiliary genre-pressure diagnostic; not used to define `audit_bucket`. |
| `genre_pressure_tercile` | Low/medium/high proxy genre pressure among computed proxy rows. |
| `keyword_semantic_quadrant` | Median-split OAI/SS quadrant from the full diagnostic panel. |
| `interpretation_prompt` | Short prompt for qualitative review. |
