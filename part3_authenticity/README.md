# Part 3: Organizational Authenticity Index

Part 3 constructs an auditable organizational authenticity proxy from the Part 1 stated-values
pages and Part 2 SEC `DEF 14A` disclosure dataset.

## What I Did

I built a deterministic company-year index that measures how closely a firm's public stated-values
theme emphasis aligns with the relative theme emphasis in its official proxy disclosure. The final
dataset keeps all 450 required company-years, computes scores for 328 company-years with sufficient
theme evidence on both sides, adds supplementary semantic similarity for rows with clean text on
both sides, and preserves explicit gap reasons for the remaining rows.

The part is implemented as a self-contained research module with source code, unit tests,
machine-readable validation, generated summaries, qualitative audit notes, and figures. The primary
deliverable is [`outputs/part3_authenticity_index.csv`](outputs/part3_authenticity_index.csv).

## Why This Design

The assignment asks for a transparent measure of alignment. Part 1 and Part 2 already use the same
12-theme taxonomy, so the most auditable approach is to compare normalized theme distributions
rather than introduce a new model. This also avoids a binary-overlap problem: proxy statements tend
to mention nearly all themes, so a presence/absence score would overstate alignment.

The primary score is:

$$
\text{authenticity\_index}=100 \times \sum_i \min(s_i,d_i)
$$

where $s_i$ is the stated-values share for theme $i$ and $d_i$ is the proxy-disclosure share for
theme $i$.

A high score means a larger share of the company's stated-values emphasis is mirrored in official
proxy disclosure emphasis. A low score is an audit signal that the two communication channels
emphasize different themes. The score is a disclosure-priority alignment proxy, not direct evidence
of actual behavior.

The main score remains deterministic and keyword-taxonomy based. A supplementary
`semantic_text_similarity` field compares representative Part 1 and Part 2 text windows with
`sentence-transformers/all-MiniLM-L6-v2`; it is reported as a robustness check, not as part of the
primary index.

## Current Results

- Final panel: 450 company-years.
- Scored rows: 328.
- Non-scored rows: 122.
- Mean score: 41.98.
- Median score: 44.83.
- Score range: 0.00 to 82.12.
- Semantic similarity computed rows: 342.
- Sector means range from 36.31 in Consumer Discretionary to 47.03 in Energy.
- The primary score is strongly correlated with cosine alignment and L1 alignment, weakly
  correlated with semantic text similarity, and near-zero correlated with Part 2 word count.
- Comparison figures show keyword, semantic, and equal-weight hybrid standards on a shared 0-100
  scale for distribution, sector, and year views.
- A keyword-vs-semantic scatter plot and qualitative case-audit notes identify divergence cases
  for human review.

Current score-status counts:

| Status | Company-years | Interpretation |
| --- | ---: | --- |
| `scored` | 328 | Part 1 and Part 2 are available and both contain deterministic theme evidence. |
| `missing_part1` | 92 | Part 1 stated-values observation is not usable. |
| `missing_part2` | 16 | Part 2 proxy disclosure is not collected. |
| `insufficient_stated_theme_signal` | 14 | Part 1 is usable, but no deterministic theme evidence was found. |

## Assumptions

- Part 1 and Part 2 outputs are final source-of-truth inputs.
- `DEF 14A` proxy statements are official disclosure evidence, not direct behavior.
- Missing source observations are not imputed.
- Usable Part 1 rows with no deterministic theme evidence are not scored.
- The deterministic taxonomy is the authoritative scoring input; embeddings and LLM outputs are
  robustness or audit context only.

## Known Limitations

- Corporate disclosure is not the same as actual organizational behavior.
- Both inputs are corporate communications, so common-method bias remains.
- Missingness is nonrandom and reduces score coverage from 450 to 328 company-years.
- Dictionary-based theme evidence can miss synonyms or count legally structured boilerplate.
- Sector norms shape both stated-values language and proxy disclosure language.
- About-page snapshots and proxy filings may not refer to exactly the same organizational period.

## What I Would Do Differently With More Time

- Add section-level proxy parsing to separate governance mechanics from substantive values language.
- Add an external validation source such as ESG controversies, employee reviews, or third-party ESG
  ratings.
- Run a larger human audit of high- and low-scoring cases.
- Compare this taxonomy-based score against alternative section-level or theme-level semantic
  similarity methods.

## Deliverables

- [`docs/summary.md`](docs/summary.md): concise nontechnical summary of the index, findings,
  comparative figures, validity and audit checks, and limitations.
- [`docs/methodology.md`](docs/methodology.md): construct definition, academic grounding, Mermaid
  workflow, LaTeX formulas, missingness rules, robustness scores, validity and audit checks, and
  limitations.
- [`docs/codebook.md`](docs/codebook.md): schema for the final dataset and supporting outputs.
- [`docs/results_snapshot.md`](docs/results_snapshot.md): generated Markdown snapshot of key
  distribution, sector, year, robustness, and quadrant tables.
- [`docs/case_audit_notes.md`](docs/case_audit_notes.md): qualitative audit notes for high,
  low, and keyword-semantic divergence cases.
- [`outputs/part3_authenticity_index.csv`](outputs/part3_authenticity_index.csv): final 450-row
  company-year panel.
- [`outputs/distribution_summary.csv`](outputs/distribution_summary.csv): overall score
  distribution.
- [`outputs/sector_summary.csv`](outputs/sector_summary.csv): sector score and missingness summary.
- [`outputs/year_summary.csv`](outputs/year_summary.csv): year score and missingness summary.
- [`outputs/company_summary.csv`](outputs/company_summary.csv): company-level average scores.
- [`outputs/validity_case_audit.csv`](outputs/validity_case_audit.csv): high/low score case audit.
- [`outputs/semantic_similarity.csv`](outputs/semantic_similarity.csv): supplementary semantic
  similarity robustness output.
- [`outputs/sensitivity_summary.csv`](outputs/sensitivity_summary.csv): robustness correlations.
- [`outputs/requirement_audit.json`](outputs/requirement_audit.json): structural validation audit.
- [`outputs/figures/score_distribution.png`](outputs/figures/score_distribution.png): primary
  score distribution.
- [`outputs/figures/sector_scores.png`](outputs/figures/sector_scores.png): primary score by
  sector.
- [`outputs/figures/year_scores.png`](outputs/figures/year_scores.png): primary score by year.
- [`outputs/figures/metric_comparison_distributions.png`](outputs/figures/metric_comparison_distributions.png):
  keyword, semantic, and hybrid distribution comparison.
- [`outputs/figures/metric_comparison_sector.png`](outputs/figures/metric_comparison_sector.png):
  keyword, semantic, and hybrid sector comparison.
- [`outputs/figures/metric_comparison_year.png`](outputs/figures/metric_comparison_year.png):
  keyword, semantic, and hybrid year comparison.
- [`outputs/figures/keyword_semantic_scatter.png`](outputs/figures/keyword_semantic_scatter.png):
  keyword-semantic quadrant scatter plot.
- [`tests/`](tests/): unit tests for theme parsing, scoring, missingness, semantic helpers, and
  validation.
- [`src/org_auth_part3/`](src/org_auth_part3/): implementation package.

## Commands

Generate the index:

```bash
PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.index
```

Generate all downstream outputs:

```bash
PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.summaries

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.semantic

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.validity

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.figures

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.presentation
```

The commands above assume the index already exists. To fully refresh Part 3 from the finalized
Part 1 and Part 2 outputs, run the modules in this order:

1. `org_auth_part3.index`
2. `org_auth_part3.summaries`
3. `org_auth_part3.validity`
4. `org_auth_part3.figures`
5. `org_auth_part3.presentation`
6. `org_auth_part3.validate`

Validate outputs:

```bash
PYTHONPATH=part3_authenticity/src \
  uv run --no-sync python -m org_auth_part3.validate
```

Run tests and lint:

```bash
PYTHONPATH=part3_authenticity/src \
  uv run --no-sync pytest part3_authenticity/tests

PYTHONPATH=part3_authenticity/src \
  uv run --no-sync ruff check part3_authenticity/src/org_auth_part3 part3_authenticity/tests
```
