# Part 1 Theme Taxonomy

## Purpose

Part 1 uses a fixed, auditable multi-label taxonomy to characterize themes in cleaned
corporate About, mission, purpose, and values pages. The implementation in
`part1_stated_values/src/org_auth_part1/analyze.py` is a reproducible keyword-and-phrase baseline.
It does not rely on model inference and returns literal source excerpts for every positive
assignment. The separate local Qwen LLM layer is documented in `docs/codebook.md` and is treated as
audit triangulation rather than as the authoritative taxonomy assignment.

This baseline supports transparent analysis and QA. It does not infer organizational intent,
judge authenticity, or replace human review. A theme that is not assigned means no configured
phrase was found; it does **not** prove that the company rejects or lacks that value.

## Version

`1.0.0-keyword-baseline`

The taxonomy version must be stored with every classification. Any change to definitions or
phrases requires a new version and a full rerun.

## Fixed Themes

| Theme ID | Meaning |
| --- | --- |
| `customers_and_service` | Serving customers, patients, clients, or consumers |
| `employees_and_workplace` | Supporting employees, talent, culture, and professional growth |
| `innovation_and_excellence` | Innovation, quality, excellence, and continuous improvement |
| `integrity_and_ethics` | Integrity, ethics, honesty, trust, and transparency |
| `diversity_equity_and_inclusion` | Diversity, equity, inclusion, belonging, and equal opportunity |
| `social_impact_and_community` | Communities, society, philanthropy, and positive social impact |
| `environment_and_sustainability` | Sustainability, climate, emissions, and natural resources |
| `health_safety_and_wellbeing` | Health, safety, security, and wellbeing |
| `shareholders_and_performance` | Shareholder value, financial performance, growth, and returns |
| `leadership_and_accountability` | Leadership, ownership, accountability, and responsibility |
| `collaboration_and_partnership` | Collaboration, teamwork, and partnerships |
| `purpose_and_identity` | Explicit purpose, mission, values, vision, and identity language |

The source code is authoritative for the exact phrase list. Phrase matching is
case-insensitive, respects word boundaries, and permits flexible whitespace.

## Academic Basis and Category Logic

This taxonomy is a deductive codebook for corporate stated-values webpages, not an unsupervised
topic model. The categories are designed to capture how firms publicly describe who they are, whom
they serve, and what principles they claim to prioritize. That is why the taxonomy combines
organizational identity language with stakeholder, CSR, sustainability, and governance-oriented
themes.

The overall coding approach follows standard content-analysis logic: define categories in advance,
apply them consistently, keep literal evidence for every positive assignment, and interpret
category counts within the limits of the source genre. This follows Krippendorff's content-analysis
work, especially the emphasis on explicit coding rules, reliability, and careful interpretation of
coded textual data. The taxonomy is therefore transparent and reproducible, but it is intentionally
not treated as a measure of sincerity or actual behavior.

The `purpose_and_identity` category is grounded in organizational identity theory. Albert and
Whetten's classic formulation treats organizational identity as what is central, distinctive, and
enduring about an organization. Corporate About, mission, purpose, and values pages are public
identity claims, so the taxonomy explicitly captures mission, purpose, values, vision, identity,
heritage, and "who we are" language.

Several categories map onto stakeholder theory. Freeman's stakeholder approach motivates separating
language about customers, employees, communities, shareholders, suppliers, partners, and other
groups affected by the firm. For this reason, the taxonomy separates `customers_and_service`,
`employees_and_workplace`, `social_impact_and_community`, `shareholders_and_performance`, and
`collaboration_and_partnership` instead of collapsing all stakeholder references into one broad
category.

The CSR and sustainability categories reflect established corporate responsibility constructs.
Carroll's CSR framework and later CSR reviews such as Aguinis and Glavas motivate attention to
ethical conduct, social/community responsibility, employee and external stakeholder concerns, and
organizational responsibility beyond immediate financial performance. Corporate sustainability
research, including Eccles, Ioannou, and Serafeim, motivates a separate
`environment_and_sustainability` category because environmental and sustainability policies are a
distinct and recurrent part of corporate values discourse. `integrity_and_ethics`,
`diversity_equity_and_inclusion`, and `health_safety_and_wellbeing` are separated because they
capture recurring normative commitments that are substantively different from general purpose or
stakeholder language.

The linguistic metrics follow computerized lexical-analysis practice rather than sentiment
analysis. Tausczik and Pennebaker's LIWC-style work supports using word categories as transparent
signals of language content and style. In this project, first-person plural language, commitment
terms, aspirational terms, action/evidence terms, stakeholder terms, and quantified claims are
auditable lexical proxies. They are descriptive indicators of how a company writes about values,
not direct measures of authenticity.

The taxonomy also follows the caution from domain-specific textual-analysis research. Loughran and
McDonald show that generic dictionaries can misclassify business and financial texts. This is why
Part 1 does not use a generic positive/negative sentiment dictionary and instead uses narrow,
inspectable phrase lists tied to corporate stated-values language, with evidence excerpts retained
for each assignment.

## Evidence Contract

Every assigned theme includes:

- `theme_id` and human-readable label
- `taxonomy_version`
- exact configured phrases that matched
- literal source sentences containing those phrases
- total match count

Positive theme assignments without evidence must fail the Part 1 requirement audit.
Unusable or missing observations receive `null`, not an empty theme list, so missing evidence
is never misrepresented as thematic absence.

## Linguistic Metrics

The baseline also calculates deterministic indicators:

- word and sentence counts
- average sentence length
- first-person plural language
- commitment language
- aspirational language
- action/evidence language
- stakeholder language
- quantified claim count

Lexicon rates are reported per 100 words. These are descriptive signals, not causal or
authenticity judgments.

## Human Review

Reviewers should inspect:

1. Every theme assignment used in a reported finding.
2. A stratified sample across themes, sectors, years, and high/low match counts.
3. False negatives caused by vocabulary not represented in the fixed phrase list.
4. False positives where a phrase appears in an irrelevant context.
5. All linguistic shifts described in the final narrative against the underlying text.

Corrections should be recorded separately with a rationale. Do not silently alter automated
output or edit the taxonomy during production.

## References

- Aguinis, H., & Glavas, A. (2012). "What We Know and Don't Know About Corporate Social
  Responsibility: A Review and Research Agenda." *Journal of Management*, 38(4), 932-968.
  https://doi.org/10.1177/0149206311436079
- Albert, S., & Whetten, D. A. (1985). "Organizational Identity." *Research in Organizational
  Behavior*, 7, 263-295.
- Carroll, A. B. (1991). "The Pyramid of Corporate Social Responsibility: Toward the Moral
  Management of Organizational Stakeholders." *Business Horizons*, 34(4), 39-48.
  https://doi.org/10.1016/0007-6813(91)90005-G
- Eccles, R. G., Ioannou, I., & Serafeim, G. (2014). "The Impact of Corporate Sustainability on
  Organizational Processes and Performance." *Management Science*, 60(11), 2835-2857.
  https://doi.org/10.1287/mnsc.2014.1984
- Freeman, R. E. (1984). *Strategic Management: A Stakeholder Approach*. Pitman.
- Krippendorff, K. (2004). "Reliability in Content Analysis: Some Common Misconceptions and
  Recommendations." *Human Communication Research*, 30(3), 411-433.
  https://doi.org/10.1111/j.1468-2958.2004.tb00738.x
- Loughran, T., & McDonald, B. (2011). "When Is a Liability Not a Liability? Textual Analysis,
  Dictionaries, and 10-Ks." *The Journal of Finance*, 66(1), 35-65.
  https://doi.org/10.1111/j.1540-6261.2010.01625.x
- Tausczik, Y. R., & Pennebaker, J. W. (2010). "The Psychological Meaning of Words: LIWC and
  Computerized Text Analysis Methods." *Journal of Language and Social Psychology*, 29(1), 24-54.
  https://doi.org/10.1177/0261927X09351676
