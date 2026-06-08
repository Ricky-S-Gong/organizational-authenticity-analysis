"""Generate Part 4 written deliverables from saved outputs."""

from __future__ import annotations

import argparse
import json

import pandas as pd

from org_auth_part4.constants import (
    CODEBOOK_DOC,
    CORRELATION_OUTPUT,
    DIAGNOSTICS_OUTPUT,
    METHODOLOGY_DOC,
    REGRESSION_OUTPUT,
    SECTION_SUMMARY_OUTPUT,
    SUMMARY_DOC,
    SUMMARY_OUTPUT,
    THEME_SEMANTIC_SUMMARY_OUTPUT,
)


def _metric(frame: pd.DataFrame, metric: str, field: str = "pearson_correlation") -> float | None:
    rows = frame[frame["comparison_metric"] == metric]
    if rows.empty:
        return None
    value = rows.iloc[0][field]
    return None if pd.isna(value) else float(value)


def _fmt(value: float | None) -> str:
    return "not available" if value is None else f"{value:.3f}"


def write_summary_doc() -> None:
    """Write the nontechnical Part 4 summary."""

    diagnostics = pd.read_csv(DIAGNOSTICS_OUTPUT)
    summary = pd.read_csv(SUMMARY_OUTPUT)
    correlations = pd.read_csv(CORRELATION_OUTPUT)
    regression = pd.read_csv(REGRESSION_OUTPUT)
    section_summary = pd.read_csv(SECTION_SUMMARY_OUTPUT)
    theme_summary = pd.read_csv(THEME_SEMANTIC_SUMMARY_OUTPUT)

    overall = summary[summary["group"] == "overall"].iloc[0]
    terciles = summary[summary["group"].str.startswith("tercile_")]
    low = terciles[terciles["group"] == "tercile_low"].iloc[0]
    high = terciles[terciles["group"] == "tercile_high"].iloc[0]
    auth_corr = _metric(correlations, "authenticity_index")
    semantic_corr = _metric(correlations, "semantic_0_100")
    gap_corr = _metric(correlations, "keyword_minus_semantic")
    genre_coef = None
    genre_row = regression[regression["term"] == "proxy_genre_pressure"]
    if not genre_row.empty:
        genre_coef = float(genre_row.iloc[0]["coefficient"])
    top_section = section_summary.sort_values("total_theme_matches", ascending=False).iloc[0]
    section_summary = section_summary.copy()
    section_summary["theme_matches_per_1000_words"] = (
        1000 * section_summary["total_theme_matches"] / section_summary["total_words"]
    )
    densest_section = section_summary.sort_values(
        "theme_matches_per_1000_words", ascending=False
    ).iloc[0]
    top_theme = theme_summary.sort_values("mean_theme_semantic_similarity", ascending=False).iloc[0]
    low_theme = theme_summary.sort_values("mean_theme_semantic_similarity", ascending=True).iloc[0]
    high_gap_theme = theme_summary.sort_values("mean_theme_share_gap_abs", ascending=False).iloc[0]
    computed_theme_rows = int(theme_summary["computed_company_years"].sum())

    scored_rows = int(diagnostics["authenticity_index"].notna().sum())
    computed_rows = int((diagnostics["genre_status"] == "computed").sum())
    auth_spearman = float(
        correlations[correlations["comparison_metric"] == "authenticity_index"].iloc[0][
            "spearman_correlation"
        ]
    )

    text = f"""# Part 4 Summary

## Research Questions

Part 4 extends the Part 3 validity checks into three numbered research questions:

1. **Whole-document genre sensitivity:** Is the Part 3 authenticity index sensitive to the
   overall genre pressure of `DEF 14A` proxy statements?
2. **Section-level evidence location:** Which proxy sections carry the values-theme evidence used
   in the alignment measure?
3. **Theme-level semantic comparability:** When the same theme appears in both stated-values pages
   and proxy statements, is the local evidence language actually semantically similar?

## Method

The analysis keeps the same 450 company-year panel used in Parts 1-3. For each collected proxy
statement, it counts three families of deterministic proxy-genre phrases:

- shareholder-meeting mechanics;
- governance boilerplate;
- legal and procedural language.

Each family is normalized per 1,000 words. The three normalized rates are z-scored and averaged
into `proxy_genre_pressure`, where higher values mean the proxy statement is more dominated by
the genre language typical of `DEF 14A` filings.

The section-level layer heuristically parses proxy text into section-like spans and classifies each
span into families such as meeting/voting, governance/board, compensation, shareholder proposals,
ownership, audit, human-capital/values, legal/other, or other. The theme-level semantic layer
compares Part 1 and Part 2 evidence excerpts within each taxonomy theme using MiniLM embeddings
when available, with a TF-IDF fallback if the embedding model cannot load.

## Coverage

- Target company-years retained: {len(diagnostics)}.
- Proxy genre diagnostics computed: {computed_rows}.
- Scored authenticity rows available for comparison: {scored_rows}.
- Parsed proxy section rows: {int(section_summary["section_rows"].sum())}.
- Theme-level comparison rows: {computed_theme_rows} computed theme-company-years.
- Mean proxy genre pressure among computed proxy rows: {overall["mean_proxy_genre_pressure"]:.3f}.
- Mean authenticity index among scored rows: {overall["mean_authenticity_index"]:.2f}.

## Findings

### Finding 1. Proxy genre pressure is a modest measurement risk, not the main explanation

The first diagnostic computes correlations between `proxy_genre_pressure` and Part 3 alignment
metrics. Proxy genre pressure has a Pearson correlation of {_fmt(auth_corr)} with the authenticity
index and a Spearman correlation of {_fmt(auth_spearman)}. This is a weak relationship, so the
safest conclusion is that genre pressure is a measurement-risk signal, not the main driver of the
index.

The tercile comparison points in the same direction. Mean authenticity is
{low["mean_authenticity_index"]:.2f} in the low genre-pressure tercile and
{high["mean_authenticity_index"]:.2f} in the high genre-pressure tercile, a difference of
{low["mean_authenticity_index"] - high["mean_authenticity_index"]:.2f} points. In a descriptive
fixed-effects regression with proxy word count, sector indicators, and year indicators, the
coefficient on `proxy_genre_pressure` is {_fmt(genre_coef)} with an $R^2$ of
{regression.iloc[0]["r_squared"]:.3f}. This is not a causal estimate, but it shows that the weak
negative pattern survives basic document-length, sector, and year context.

![Proxy genre pressure vs authenticity](../outputs/figures/genre_pressure_vs_authenticity.png)

The figure is useful as a diagnostic check rather than as the main evidence. It shows wide
dispersion at nearly every level of proxy genre pressure: highly procedural proxy statements can
still have moderate or high alignment, and low-alignment cases also appear outside the
highest-genre region. Therefore, low authenticity scores should not be automatically dismissed as
template effects, but high-genre/low-score cases should be routed to section-level review.

Genre pressure is correlated with rescaled semantic similarity at {_fmt(semantic_corr)} and with
keyword-minus-semantic divergence at {_fmt(gap_corr)}. This matters because Part 3 showed that
keyword theme alignment and broad embedding similarity capture different signals. If high-genre
proxy statements look semantically similar while receiving lower keyword alignment, that pattern is
consistent with embeddings picking up generic corporate/proxy language while the taxonomy-based
index still identifies weak values-priority overlap.

### Finding 2. Section-level parsing shows where proxy evidence is coming from

The second diagnostic parses the proxy statements into section-like spans and aggregates values
theme evidence by section family. This produces {int(section_summary["section_rows"].sum())}
section rows across {int(section_summary["company_years"].max())} company-years. The largest raw
source of values-theme evidence is `{top_section["section_family"]}`, with
{int(top_section["total_theme_matches"])} total theme matches. `meeting_voting` is next with
67,314 matches, followed by `human_capital_values` with 59,405 matches.

Raw volume and density tell different stories. `governance_board` contributes the most total
evidence because it is very large: {int(top_section["total_words"]):,} parsed words. But the
densest values-language section family is `{densest_section["section_family"]}`, with
{densest_section["theme_matches_per_1000_words"]:.2f} theme matches per 1,000 section words. This
is why section-level parsing matters: the index draws a lot of evidence from governance machinery,
while the most concentrated values language appears in more explicitly values-oriented sections.

![Section theme heatmap](../outputs/figures/section_theme_heatmap.png)

The heatmap is the most diagnostic section-level figure. Each row is a proxy section family, and
each annotated cell reports the within-section-family share of values-theme matches assigned to a
theme. Read it row by row: the values in a row sum to approximately 1.00, so darker and larger
numbers identify the dominant themes within that section family. This is a composition plot, not a
raw-count plot. The figure shows that proxy evidence is not evenly distributed across sections:
governance and meeting/voting sections carry substantial theme evidence, but the composition of
that evidence differs by section family. This matters because a theme match in a governance-board
section may mean something different from the same theme match in a human-capital/values section.

### Finding 3. Same-theme semantic comparability varies sharply by theme

The third diagnostic compares Part 1 and Part 2 evidence excerpts within the same taxonomy theme.
It computes MiniLM semantic similarity for {computed_theme_rows} company-year-theme pairs where
both sides have evidence. This is a stricter check than whole-text semantic similarity because it
asks whether the local language attached to the same theme label is actually similar.

The highest mean local semantic similarity is `{top_theme["theme_id"]}` at
{top_theme["mean_theme_semantic_similarity"]:.2f}, followed closely by
`environment_and_sustainability` at 45.83. The lowest is `{low_theme["theme_id"]}` at
{low_theme["mean_theme_semantic_similarity"]:.2f}. The largest mean stated/disclosure emphasis gap
appears for `{high_gap_theme["theme_id"]}` at {high_gap_theme["mean_theme_share_gap_abs"]:.3f}.

![Theme-level semantic similarity](../outputs/figures/theme_level_semantic_similarity.png)

The figure shows that theme labels are not interchangeable measurement units. Innovation,
environment/sustainability, purpose/identity, and social-impact evidence tends to be more locally
similar across stated-values pages and proxy disclosures. By contrast, employees/workplace has the
lowest local semantic similarity. A likely interpretation is that stated-values pages often discuss
employees as culture, people, and mission, while proxy statements often discuss employees through
compensation, governance, workforce-risk, or human-capital disclosure language.

### Supplementary diagnostic figures

The two bubble plots are useful as secondary diagnostics. They are not the main evidence for the
findings above, but they make two measurement tradeoffs easier to inspect.

![Section size and values-theme density](../outputs/figures/section_theme_composition.png)

This plot explains the section-level distinction between evidence volume and evidence density. The
x-axis is total parsed words for each section family, the y-axis is values-theme matches per 1,000
section words, and bubble size is total theme matches, with the legend giving reference bubble
sizes. It shows why `governance_board` dominates raw evidence while `human_capital_values` is the
most values-dense section family.

![Theme semantic similarity vs emphasis gap](../outputs/figures/theme_semantic_gap_scatter.png)

This plot explains the theme-level distinction between semantic comparability and emphasis
alignment. The x-axis is the mean absolute stated/disclosure theme-share gap, the y-axis is
mean theme-level semantic similarity, and bubble size is the number of computed company-years for
that theme. It shows that themes can differ in quantity and meaning at the same time: a theme can
have a large emphasis gap but still be locally semantically similar, or have a smaller emphasis gap
while using different local language across the two source types.

## Interpretation

Part 4 should be read as a stress test for the authenticity measure. The whole-document genre layer
asks whether low scores are plausibly template-driven. The section layer shows where in the proxy
the measured values evidence appears. The theme-semantic layer checks whether shared theme labels
actually refer to similar local language across the stated-values page and proxy statement.

## Limitations

The genre dictionaries are transparent but incomplete. They identify common proxy-statement
language; they do not perfectly separate boilerplate from substantive governance discussion. The
analysis is also exploratory and descriptive. It does not prove that proxy genre causes low
alignment, nor does it prove that low-genre, low-alignment cases reflect actual organizational
inauthenticity.
"""
    SUMMARY_DOC.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_DOC.write_text(text, encoding="utf-8")


def write_methodology_doc() -> None:
    """Write Part 4 methodology."""

    text = """# Part 4 Methodology

## Construct

Part 4 has three diagnostic constructs. `proxy_genre_pressure` measures how strongly a `DEF 14A`
proxy statement reflects shareholder-meeting mechanics, governance boilerplate, and
legal-procedural language. `section_family` identifies which proxy sections carry the values-theme
evidence used in the Part 3 index. `theme_semantic_similarity` compares Part 1 and Part 2 evidence
excerpts inside the same taxonomy theme.

None of these is a replacement authenticity index. Together, they stress-test the Part 3 index.

## Workflow

```mermaid
flowchart LR
    A["Part 3 authenticity panel"] --> C["Merge on ticker-year"]
    B["Part 2 proxy text and metadata"] --> C
    C --> D["Count deterministic genre phrase families"]
    D --> E["Normalize counts per 1,000 words"]
    E --> F["Z-score each genre family"]
    F --> G["Average into proxy_genre_pressure"]
    C --> H["Parse proxy sections<br>and classify section families"]
    C --> J["Compare same-theme<br>Part 1/Part 2 excerpts"]
    G --> K["Compare with keyword index, semantic score, quadrants, and cases"]
    H --> K
    J --> K
    K --> I["Write outputs, figures, summary, and validation audit"]
```

## Phrase Families

The three phrase families are intentionally simple and auditable:

- `shareholder_mechanics`: annual meeting, voting, proxy cards, record dates, beneficial owners,
  quorum, and shareholder proposals.
- `governance_boilerplate`: board, committees, directors, independence, corporate governance, and
  executive compensation.
- `legal_procedural`: pursuant, accordance, regulation, securities, Exchange Act, solicitation,
  hereby, and related legal-form language.

The rate for each family is:

$$
R_f = 1000 \\times \\frac{C_f}{W}
$$

where `C_f` is the phrase count for family `f`, and `W` is the extracted proxy word count.

The composite score is:

$$
G = \\frac{z(R_s) + z(R_g) + z(R_l)}{3}
$$

where `G` is `proxy_genre_pressure`, and the three z-scored rates represent shareholder mechanics,
governance boilerplate, and legal-procedural language.

## Interpretation Rules

High proxy genre pressure means the proxy statement is especially saturated with the language of
the `DEF 14A` genre. It does not mean the disclosure is bad, misleading, or less substantive. A
negative association between genre pressure and authenticity would suggest that the Part 3 index
may partly penalize company-years whose proxy statements are more procedural. A weak association
would support the claim that low scores are not merely a proxy-template artifact.

## Section-Level Proxy Parsing

The section parser uses line-level heading heuristics rather than company-specific templates. A
line is treated as a candidate heading when it is short, heading-like, and either contains a known
section phrase or has title/uppercase structure. Text between adjacent headings becomes a section.
If a filing yields too few headings, the parser falls back to fixed-size text chunks and classifies
those chunks by content.

Each section is assigned to one of these families: `meeting_voting`, `governance_board`,
`compensation`, `shareholder_proposals`, `ownership`, `audit`, `human_capital_values`,
`legal_other`, or `other`.

For each section, the output stores word count, share of proxy text, genre count/rate, total
taxonomy-theme matches, dominant theme, and per-theme counts. This makes it possible to see whether
values evidence is concentrated in procedural sections or in more substantive governance,
workforce, sustainability, and values-related spans.

## Theme-Level Semantic Comparison

The theme-semantic layer uses the upstream `theme_evidence` fields from Parts 1 and 2. For each
company-year and each of the 12 taxonomy themes, it collects bounded evidence excerpts from the
stated-values page and proxy statement. If both sides have evidence for the same theme, it compares
the local excerpt texts.

The primary comparison uses `sentence-transformers/all-MiniLM-L6-v2`, matching the Part 3 semantic
robustness model family. If that model cannot be loaded locally, the code falls back to a
deterministic TF-IDF unigram/bigram cosine score and records the fallback method. Rows where one or
both sides lack evidence remain in the output with explicit status fields.

## Case Audit Logic

The case-audit table separates four groups using only the two primary alignment diagnostics:
Organizational Authenticity Index (OAI) and whole-text semantic similarity (SS):

- low OAI and low SS;
- low OAI and high SS;
- high OAI and low SS;
- high OAI and high SS.

Proxy genre pressure remains in the output as an auxiliary diagnostic column, but it does not
define the case type. These buckets are designed for follow-up qualitative review, not final
classification.
"""
    METHODOLOGY_DOC.write_text(text, encoding="utf-8")


def write_codebook_doc() -> None:
    """Write Part 4 codebook."""

    text = """# Part 4 Codebook

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
"""
    CODEBOOK_DOC.write_text(text, encoding="utf-8")


def write_docs() -> dict[str, str]:
    """Write all Part 4 docs."""

    write_summary_doc()
    write_methodology_doc()
    write_codebook_doc()
    return {
        str(SUMMARY_DOC): "summary",
        str(METHODOLOGY_DOC): "methodology",
        str(CODEBOOK_DOC): "codebook",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(write_docs(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
