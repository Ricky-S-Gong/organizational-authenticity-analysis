"""Create Part 2 research-facing tables and narrative from saved analysis outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from org_auth_part2.targets import PART2_ROOT
from org_auth_part2.text_mining import DEFAULT_OUTPUT_DIR

DEFAULT_TABLE_DIR = PART2_ROOT / "outputs/text_mining/tables"
DEFAULT_ANALYSIS_DOC = PART2_ROOT / "docs/text_mining_analysis.md"
DEFAULT_SUMMARY_DOC = PART2_ROOT / "docs/summary.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: str | float, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def latex_table(headers: list[str], rows: list[list[str]], caption: str, label: str) -> str:
    cols = "l" * len(headers)
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{cols}}}",
        "\\hline",
        " & ".join(headers) + " \\\\",
        "\\hline",
    ]
    for row in rows:
        escaped = [cell.replace("&", "\\&").replace("%", "\\%") for cell in row]
        lines.append(" & ".join(escaped) + " \\\\")
    lines.extend(["\\hline", "\\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def write_table_set(
    table_dir: Path,
    name: str,
    headers: list[str],
    rows: list[list[str]],
    caption: str,
) -> None:
    table_dir.mkdir(parents=True, exist_ok=True)
    (table_dir / f"{name}.md").write_text(markdown_table(headers, rows), encoding="utf-8")
    (table_dir / f"{name}.tex").write_text(
        latex_table(headers, rows, caption, f"tab:{name}"),
        encoding="utf-8",
    )


def build_tables(output_dir: Path, table_dir: Path) -> dict[str, Any]:
    summary = json.loads((output_dir / "text_mining_summary.json").read_text(encoding="utf-8"))
    theme_sector = read_csv(output_dir / "theme_sector_summary.csv")
    adjacent = read_csv(output_dir / "top_adjacent_theme_shifts.csv")
    missing = read_csv(output_dir / "missing_summary.csv")
    linguistic_year = read_csv(output_dir / "linguistic_year_summary.csv")
    sector_linguistic = read_csv(output_dir / "sector_linguistic_summary.csv")
    event = summary["event_window_theme_changes"]

    overall_rows = [
        [
            row["theme_label"],
            fmt(row["mean_matches_per_10k_words"]),
            f"{float(row['presence_rate']) * 100:.1f}%",
        ]
        for row in summary["top_overall_themes"]
    ]
    write_table_set(
        table_dir,
        "overall_theme_emphasis",
        ["Theme", "Mean matches / 10k words", "Presence"],
        overall_rows,
        "Overall normalized theme emphasis in Part 2 proxy statements.",
    )

    sector_rows = []
    for sector_payload in summary["sector_leading_themes"]:
        sector_rows.append(
            [
                sector_payload["sector"],
                "; ".join(
                    f"{row['theme_label']} ({float(row['mean_matches_per_10k_words']):.1f})"
                    for row in sector_payload["leading_themes"][:3]
                ),
            ]
        )
    write_table_set(
        table_dir,
        "sector_leading_themes",
        ["Sector", "Top normalized themes"],
        sector_rows,
        "Leading themes by sector, normalized by document length.",
    )

    event_rows = [
        [
            row["theme_label"],
            fmt(row["pre_2020_rate"]),
            fmt(row["covid_dei_governance_window_rate"]),
            fmt(row["post_2021_rate"]),
            fmt(row["window_minus_pre"]),
        ]
        for row in event[:8]
    ]
    write_table_set(
        table_dir,
        "event_window_theme_changes",
        ["Theme", "Pre-2020", "2020-2021", "Post-2021", "Window - pre"],
        event_rows,
        "Descriptive event-window differences in normalized theme emphasis.",
    )
    event_shift_rows = [
        [
            "2020-2021",
            "COVID-era workforce shock",
            "Employees/workplace +6.25; health/safety +3.08 vs. pre-2020",
            "Proxy language becomes more attentive to workforce continuity, safety, "
            "and employee-facing governance.",
            "Descriptive coincidence only; proxy templates and workforce disclosure norms "
            "also changed.",
        ],
        [
            "2020-2021",
            "Post-2020 DEI attention",
            "DEI +6.76 vs. pre-2020",
            "Diversity, equity, and inclusion language becomes more prominent in governance "
            "disclosures.",
            "Some DEI matches appear in shareholder proposal or voting mechanics, so excerpt "
            "review remains necessary.",
        ],
        [
            "2021 onward",
            "Investor attention to ESG governance",
            "Environment/sustainability rises from 8.06 pre-2020 to 21.71 post-2021",
            "Sustainability language continues increasing after the initial 2020-2021 window.",
            "The evidence supports a timing association, not a causal estimate of ESG pressure.",
        ],
    ]
    write_table_set(
        table_dir,
        "event_shift_interpretation",
        ["Window", "Relevant external event", "Observed text shift", "Interpretation", "Caveat"],
        event_shift_rows,
        "External-event windows and coincident text shifts in Part 2 proxy statements.",
    )

    tone_year_rows = [
        [
            row["year"],
            fmt(row["mean_first_person_plural_rate_per_100_words"], 3),
            fmt(row["mean_commitment_rate_per_100_words"], 3),
            fmt(row["mean_action_or_evidence_rate_per_100_words"], 3),
            fmt(row["mean_stakeholder_rate_per_100_words"], 3),
            fmt(row["mean_average_sentence_length"], 2),
        ]
        for row in linguistic_year
    ]
    write_table_set(
        table_dir,
        "language_tone_over_time",
        [
            "Year",
            "Collective voice",
            "Commitment",
            "Action/evidence",
            "Stakeholder",
            "Avg sentence length",
        ],
        tone_year_rows,
        "Language and tone indicators over time in collected proxy statements.",
    )

    tone_sector_rows = [
        [
            row["sector"],
            fmt(row["mean_first_person_plural_rate_per_100_words"], 3),
            fmt(row["mean_commitment_rate_per_100_words"], 3),
            fmt(row["mean_action_or_evidence_rate_per_100_words"], 3),
            fmt(row["mean_stakeholder_rate_per_100_words"], 3),
            fmt(row["mean_average_sentence_length"], 2),
        ]
        for row in sector_linguistic
    ]
    write_table_set(
        table_dir,
        "sector_language_tone",
        [
            "Sector",
            "Collective voice",
            "Commitment",
            "Action/evidence",
            "Stakeholder",
            "Avg sentence length",
        ],
        tone_sector_rows,
        "Language and tone indicators by sector in collected proxy statements.",
    )

    shift_rows = [
        [
            row["ticker"],
            f"{row['prior_year']}-{row['year']}",
            row["theme_label"],
            fmt(row["change_per_10k_words"]),
        ]
        for row in adjacent[:10]
    ]
    write_table_set(
        table_dir,
        "largest_adjacent_theme_shifts",
        ["Ticker", "Years", "Theme", "Change / 10k words"],
        shift_rows,
        "Largest adjacent-year theme shifts in collected proxy statements.",
    )

    missing_rows = [
        [row["ticker"], row["sector"], row["missing_years"], row["missing_count"]]
        for row in missing
    ]
    write_table_set(
        table_dir,
        "missing_company_years",
        ["Ticker", "Sector", "Missing years", "Count"],
        missing_rows,
        "Part 2 company-years without a selected DEF 14A filing.",
    )

    technology_dei = next(
        row
        for row in theme_sector
        if row["sector"] == "Technology" and row["theme_id"] == "diversity_equity_and_inclusion"
    )
    energy_environment = next(
        row
        for row in theme_sector
        if row["sector"] == "Energy" and row["theme_id"] == "environment_and_sustainability"
    )
    technology_tone = next(row for row in sector_linguistic if row["sector"] == "Technology")
    financials_tone = next(row for row in sector_linguistic if row["sector"] == "Financials")
    return {
        "summary": summary,
        "technology_dei": float(technology_dei["mean_matches_per_10k_words"]),
        "energy_environment": float(energy_environment["mean_matches_per_10k_words"]),
        "tone_first_year": linguistic_year[0],
        "tone_last_year": linguistic_year[-1],
        "technology_tone": technology_tone,
        "financials_tone": financials_tone,
        "overall_rows": overall_rows,
        "sector_rows": sector_rows,
        "event_rows": event_rows,
        "event_shift_rows": event_shift_rows,
        "tone_year_rows": tone_year_rows,
        "tone_sector_rows": tone_sector_rows,
        "shift_rows": shift_rows,
        "missing_rows": missing_rows,
    }


def write_docs(payload: dict[str, Any], table_dir: Path) -> None:
    summary = payload["summary"]
    figures_rel = "../outputs/text_mining/figures"
    collective_start = float(
        payload["tone_first_year"]["mean_first_person_plural_rate_per_100_words"]
    )
    collective_end = float(
        payload["tone_last_year"]["mean_first_person_plural_rate_per_100_words"]
    )
    collective_increase = ((collective_end / collective_start) - 1) * 100
    stakeholder_start = float(payload["tone_first_year"]["mean_stakeholder_rate_per_100_words"])
    stakeholder_end = float(payload["tone_last_year"]["mean_stakeholder_rate_per_100_words"])
    commitment_start = float(payload["tone_first_year"]["mean_commitment_rate_per_100_words"])
    commitment_end = float(payload["tone_last_year"]["mean_commitment_rate_per_100_words"])
    tone_bullets = "\n".join(
        [
            "- Collective voice rises from "
            f"{collective_start:.3f} to {collective_end:.3f} markers per 100 words, "
            f"a roughly {collective_increase:.1f}% increase.",
            "- Stakeholder orientation rises from "
            f"{stakeholder_start:.3f} in {payload['tone_first_year']['year']} to a "
            f"2021 peak of 0.324, and remains higher in "
            f"{payload['tone_last_year']['year']} at {stakeholder_end:.3f}.",
            "- Commitment language declines from "
            f"{commitment_start:.3f} to {commitment_end:.3f}, while action/evidence terms "
            "stay low, around 0.08-0.10 markers per 100 words.",
        ]
    )
    analysis = f"""# Part 2 Text Mining Analysis

## Research Design and Method

Part 2 analyzes SEC `DEF 14A` proxy statements as a free, official, and reproducible disclosure
source. The full run covers {summary["collected_rows"]} of 450 company-years
({summary["coverage_rate"]:.2%}). The remaining {summary["missing_rows"]} rows are retained as
documented gaps and are not imputed.

The analysis has two layers. The main evidentiary layer is deterministic: Part 1-compatible theme
matching, literal phrase evidence, document-length-normalized rates, and descriptive linguistic
metrics. This layer carries the main claims because it is transparent, reproducible, and easy to
audit.

A second, exploratory layer adds open-source model-based checks: TF-IDF/NMF topic modeling,
MiniLM sentence embeddings, spaCy features, and a sampled local FLAN-T5 annotation pass. These
model outputs are used for triangulation, construct-validity checks, and audit triage; they do not
replace the deterministic phrase-evidence baseline. I did not use a paid API or closed model.

I treat `language` as the vocabulary and phrase emphasis captured by the theme taxonomy, and `tone`
as observable disclosure style: collective voice, commitment language, aspirational language,
action/evidence language, stakeholder orientation, sentence length, and quantified claims. These
are lexical proxies rather than psychological sentiment scores, which is more appropriate for legal
proxy filings.

## 1. Overall Disclosure Priorities

![Theme emphasis over time]({figures_rel}/theme_over_time.png)

{(table_dir / "overall_theme_emphasis.md").read_text(encoding="utf-8")}

The strongest overall signal is not surprising: proxy statements are shareholder-facing governance
documents, so `Shareholders and performance` is the top normalized theme at
{summary["top_overall_themes"][0]["mean_matches_per_10k_words"]:.1f} matches per 10,000 words.
What is more substantively useful is that workforce and DEI language are also pervasive. `Employees
and workplace` and `Diversity, equity, and inclusion` appear in every collected company-year and
rank second and third by normalized intensity. This suggests that by 2016-2024, proxy statements
were no longer only compensation and voting documents; they had become a venue for communicating
human-capital and governance identity claims.

## 2. Cross-Sector Comparison

![Sector theme heatmap]({figures_rel}/sector_theme_heatmap.png)

{(table_dir / "sector_leading_themes.md").read_text(encoding="utf-8")}

The sector comparison shows both document-type regularity and meaningful heterogeneity.
Consumer discretionary, healthcare, and financial firms are especially shareholder/performance
heavy. Technology is distinctive: its highest normalized theme is DEI at
{payload["technology_dei"]:.1f} matches per 10,000 words. Energy is also distinctive: environment
and sustainability reaches {payload["energy_environment"]:.1f} matches per 10,000 words, much
higher than the overall mean, but employee/workplace language remains the sector's top category.
These differences are useful for Part 3 because an alignment measure should not treat all sectors
as having the same expected disclosure vocabulary.

## 3. Time and External-Event Window

![Event-window theme change]({figures_rel}/event_window_theme_change.png)

{(table_dir / "event_window_theme_changes.md").read_text(encoding="utf-8")}

The 2020-2021 window shows the clearest descriptive increase in themes tied to workforce, DEI,
sustainability, and stakeholder concern. DEI rises by 6.76 matches per 10,000 words relative to the
pre-2020 period; employee/workplace language rises by 6.25; and environment/sustainability rises by
4.94. These changes are consistent with the COVID-era workforce shock, the post-2020 DEI disclosure
cycle, and growing investor attention to ESG governance. They should not be interpreted as causal
effects: proxy templates, regulatory expectations, and investor norms changed at the same time.

The event interpretation table makes the external-event claim explicit. It links each external
context to the text shift it appears to coincide with, while keeping the causal caveat visible.

{(table_dir / "event_shift_interpretation.md").read_text(encoding="utf-8")}

## 4. Language and Tone Over Time

The central language-and-tone finding is that proxy disclosures become more stakeholder-facing and
more explicitly organizational in voice over time, but not more action-heavy. This is different from
the theme result. The theme analysis asks *what topics* appear; the tone analysis asks *how the
filings speak* when they discuss governance, human capital, and corporate priorities.

{tone_bullets}

Substantively, this means the corpus does not simply add more values topics. It increasingly frames
those topics through an institutional `we/our` voice and a broader stakeholder vocabulary, while
still preserving the cautious, formal style of proxy disclosure.

![Language and tone over time]({figures_rel}/language_tone_over_time.png)

{(table_dir / "language_tone_over_time.md").read_text(encoding="utf-8")}

The indexed line chart makes the shift easier to read than raw rates alone. Stakeholder orientation
increases most sharply through 2021, consistent with the COVID-era and post-2020 shift toward
workforce, DEI, health/safety, and ESG governance language. Collective voice rises more steadily
across the full window. Commitment language does not show the same increase; by 2024 it is below
its 2016 level. This contrast is important because it suggests a change in disclosure stance, not
just a uniform increase in all positive-sounding values language.

![Sector language and tone heatmap]({figures_rel}/sector_tone_heatmap.png)

{(table_dir / "sector_language_tone.md").read_text(encoding="utf-8")}

Sector-level tone also varies. Technology has the strongest collective-voice rate at
{float(payload["technology_tone"]["mean_first_person_plural_rate_per_100_words"]):.3f} per 100
words and the highest commitment rate at
{float(payload["technology_tone"]["mean_commitment_rate_per_100_words"]):.3f}. Financials have the
highest stakeholder-orientation rate at
{float(payload["financials_tone"]["mean_stakeholder_rate_per_100_words"]):.3f}. This reinforces the
theme results: sector differences are not only about which topics appear, but also about how firms
style their disclosure voice.

## 5. Within-Company Shifts

{(table_dir / "largest_adjacent_theme_shifts.md").read_text(encoding="utf-8")}

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

## 6. Coverage and Missingness

{(table_dir / "missing_company_years.md").read_text(encoding="utf-8")}

Coverage is high enough for descriptive text mining, but missingness is not random enough to ignore.
BlackRock accounts for nine of the sixteen gaps, and Broadcom accounts for three. For Part 3, these
company-years should remain missing rather than being assigned zero disclosure emphasis or filled
with sector means.

## Interpretation

The core empirical takeaway is that proxy statements reveal a structured hierarchy of disclosed
priorities: shareholder/performance language remains dominant, but workforce, DEI, leadership, and
sustainability language are substantial and vary by sector and time. The construct-validity caveat
is central: this is evidence about disclosed priorities in legally structured corporate
communications, not direct evidence of lived organizational behavior.
"""
    DEFAULT_ANALYSIS_DOC.write_text(analysis, encoding="utf-8")

    final_summary = f"""# Part 2 Summary

## Scope

Part 2 collects and analyzes lived-values disclosures for the same 50 companies and 2016-2024
company-year window used in Part 1. The selected disclosure type is SEC `DEF 14A` proxy
statements.

## Coverage

- Target rows: 450
- Collected proxy statements: {summary["collected_rows"]} of 450 ({summary["coverage_rate"]:.2%})
- Missing rows: {summary["missing_rows"]}
- Document type: SEC `DEF 14A`
- Source: SEC EDGAR submissions API and Archives

Missing rows are retained with structured gap reasons and are not imputed or treated as zero
disclosure.

## Method

The pipeline resolves tickers to SEC CIKs, retrieves company submissions metadata, selects the
calendar-year `DEF 14A` filing, downloads the primary filing document, extracts clean text, and
records source metadata and SHA256 hashes. The final compact dataset keeps company-year status,
SEC filing identifiers, source URLs, text metrics, theme categories, phrase evidence, and
linguistic metrics.

The baseline analysis uses a deterministic Part 1-compatible keyword taxonomy and normalizes theme
matches per 10,000 words. Language and tone are measured with auditable lexical indicators,
including collective voice, commitment terms, action/evidence terms, stakeholder orientation,
sentence length, and quantified claims. An enhanced exploratory layer adds TF-IDF/NMF topics,
MiniLM embeddings, spaCy features, and sampled local FLAN-T5 annotations, but these model-based
outputs are kept separate from the baseline phrase-evidence results.

## Findings

Proxy disclosures are dominated by shareholder and performance language, which is expected for
shareholder-facing governance documents. Employee/workplace, diversity/equity/inclusion, and
leadership/accountability language are also consistently present across the collected filings.

The language-and-tone analysis adds a distinct finding beyond topic prevalence. Collective voice
(`we/our/us`) increases from {collective_start:.3f} to {collective_end:.3f} markers per 100 words,
and stakeholder-oriented language remains higher in 2024 than in 2016 after peaking in 2021. By
contrast, commitment markers decline and action/evidence markers remain low. This suggests that
proxy disclosures become more stakeholder-facing and organizational in voice, but not more
narratively action-heavy.

The external-event analysis is descriptive rather than causal. The 2020-2021 window shows
increases in DEI, employee/workplace, sustainability, and health/safety language relative to the
pre-2020 period. These shifts appear to coincide with COVID-era workforce concerns, post-2020 DEI
attention, and ESG governance pressure. The post-2021 sustainability rate remains especially
elevated, which is consistent with continued investor attention to ESG governance.

The enhanced model checks reinforce the construct-validity caveat: NMF mostly recovers
proxy-structure topics such as shareholder meetings, stockholder proposals, forward-looking
statements, and annual meeting mechanics. This suggests that lived-values language in `DEF 14A`
filings is embedded within governance machinery rather than presented as a clean cultural
manifesto.

## Limitation

`DEF 14A` filings are official, free, and highly auditable, but they are not direct observations of
organizational behavior. Part 2 should therefore be interpreted as evidence of disclosed
governance and human-capital priorities, not as proof of lived values. Missing company-years should
remain missing in downstream alignment analysis.
"""
    DEFAULT_SUMMARY_DOC.write_text(final_summary, encoding="utf-8")


def build_presentation(output_dir: Path, table_dir: Path) -> dict[str, Any]:
    payload = build_tables(output_dir, table_dir)
    write_docs(payload, table_dir)
    return {
        "table_dir": str(table_dir),
        "analysis_doc": str(DEFAULT_ANALYSIS_DOC),
        "summary_doc": str(DEFAULT_SUMMARY_DOC),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Part 2 presentation tables and docs.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--table-dir", type=Path, default=DEFAULT_TABLE_DIR)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print(json.dumps(build_presentation(args.output_dir, args.table_dir), indent=2))


if __name__ == "__main__":
    main()
