# Part 1 Theme Taxonomy

## Purpose

Part 1 uses a fixed, auditable multi-label taxonomy to characterize themes in cleaned
corporate About, mission, purpose, and values pages. The implementation in
`src/org_auth_part1/analyze.py` is a reproducible keyword-and-phrase baseline. It requires no
external LLM credentials and returns literal source excerpts for every positive assignment.

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
