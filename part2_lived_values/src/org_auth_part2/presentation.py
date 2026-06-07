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
    return {
        "summary": summary,
        "technology_dei": float(technology_dei["mean_matches_per_10k_words"]),
        "energy_environment": float(energy_environment["mean_matches_per_10k_words"]),
        "overall_rows": overall_rows,
        "sector_rows": sector_rows,
        "event_rows": event_rows,
        "shift_rows": shift_rows,
        "missing_rows": missing_rows,
    }


def write_docs(payload: dict[str, Any], table_dir: Path) -> None:
    summary = payload["summary"]
    tables_rel = "../outputs/text_mining/tables"
    figures_rel = "../outputs/text_mining/figures"
    analysis = f"""# Part 2 Text Mining Analysis

## Research Design and Method

Part 2 analyzes SEC `DEF 14A` proxy statements as a free, official, and reproducible disclosure
source. The full run covers {summary["collected_rows"]} of 450 company-years
({summary["coverage_rate"]:.2%}). The remaining {summary["missing_rows"]} rows are retained as
documented gaps and are not imputed.

The analysis uses deterministic text mining only: Part 1-compatible theme matching, literal phrase
evidence, document-length-normalized rates, and descriptive linguistic metrics. I did not use a
paid API, closed model, or external LLM. This keeps the analysis auditable and appropriate for a
small RA interview assignment.

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

## 4. Within-Company Shifts

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

## 5. Coverage and Missingness

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

Part 2 uses SEC `DEF 14A` proxy statements as the single lived-values disclosure type. The full run
collected {summary["collected_rows"]} of 450 company-years ({summary["coverage_rate"]:.2%}).
The 16 missing rows are documented and not imputed.

The text-mining analysis uses deterministic, free, reproducible methods only: Part 1-compatible
theme matching, phrase evidence, normalized rates per 10,000 words, and descriptive linguistic
metrics. No paid API, closed model, or external LLM was used.

The main result is that proxy disclosures are dominated by shareholder/performance language
({summary["top_overall_themes"][0]["mean_matches_per_10k_words"]:.1f} matches per 10,000 words),
but employee/workplace, DEI, and leadership/accountability language are also pervasive. Cross-sector
variation is meaningful: technology is strongest on DEI, energy is unusually high on
environment/sustainability, and financials/healthcare/consumer discretionary remain more
shareholder/performance heavy.

The 2020-2021 event window shows descriptive increases in DEI, employee/workplace, sustainability,
and health/safety language relative to pre-2020 levels. These shifts are plausible in light of
COVID-era workforce concerns, post-2020 DEI attention, and ESG governance pressure, but they are
not causal estimates.

Saved figures:

- `{figures_rel}/theme_over_time.png`
- `{figures_rel}/sector_theme_heatmap.png`
- `{figures_rel}/event_window_theme_change.png`

Saved Markdown and LaTeX tables live in `{tables_rel}/`.
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
