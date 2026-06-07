"""Deterministic Part 2 text-mining analysis for collected proxy statements."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from org_auth_part2.analyze import THEME_TAXONOMY
from org_auth_part2.run import DEFAULT_DATASET
from org_auth_part2.targets import PART2_ROOT

DEFAULT_OUTPUT_DIR = PART2_ROOT / "outputs/text_mining"
DEFAULT_ANALYSIS_DOC = PART2_ROOT / "docs/text_mining_analysis.md"
DEFAULT_SUMMARY_DOC = PART2_ROOT / "docs/summary.md"

THEME_LABELS = {theme.theme_id: theme.label for theme in THEME_TAXONOMY}
EVENT_WINDOWS = {
    "pre_2020": tuple(range(2016, 2020)),
    "covid_dei_governance_window": (2020, 2021),
    "post_2021": (2022, 2023, 2024),
}
LINGUISTIC_RATE_FIELDS = (
    "first_person_plural_rate_per_100_words",
    "commitment_rate_per_100_words",
    "aspiration_rate_per_100_words",
    "action_or_evidence_rate_per_100_words",
    "stakeholder_rate_per_100_words",
    "average_sentence_length",
    "quantified_claim_count",
)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _median(values: list[float]) -> float:
    return round(statistics.median(values), 6) if values else 0.0


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def read_dataset(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    csv.field_size_limit(sys.maxsize)
    collected: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["collection_status"] != "collected":
                missing.append(row)
                continue
            metrics = json.loads(row["linguistic_metrics"])
            evidence = json.loads(row["theme_evidence"])
            theme_counts = {
                theme["theme_id"]: int(theme["match_count"])
                for theme in evidence
                if theme.get("theme_id")
            }
            word_count = int(row["word_count"])
            collected.append(
                {
                    "ticker": row["ticker"],
                    "company_name": row["company_name"],
                    "sector": row["sector"],
                    "year": int(row["year"]),
                    "word_count": word_count,
                    "sentence_count": int(row["sentence_count"]),
                    "theme_counts": theme_counts,
                    "linguistic_metrics": metrics,
                }
            )
    return collected, missing


def theme_rate(row: dict[str, Any], theme_id: str) -> float:
    count = row["theme_counts"].get(theme_id, 0)
    return (count / row["word_count"]) * 10_000 if row["word_count"] else 0.0


def theme_year_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for theme_id in THEME_LABELS:
            grouped[(row["year"], theme_id)].append(row)
    output: list[dict[str, Any]] = []
    for (year, theme_id), group in sorted(grouped.items()):
        rates = [theme_rate(row, theme_id) for row in group]
        presence = [1 for row in group if row["theme_counts"].get(theme_id, 0) > 0]
        output.append(
            {
                "year": year,
                "theme_id": theme_id,
                "theme_label": THEME_LABELS[theme_id],
                "company_years": len(group),
                "presence_rate": _pct(len(presence), len(group)),
                "mean_matches_per_10k_words": _mean(rates),
                "median_matches_per_10k_words": _median(rates),
                "total_matches": sum(row["theme_counts"].get(theme_id, 0) for row in group),
            }
        )
    return output


def theme_sector_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for theme_id in THEME_LABELS:
            grouped[(row["sector"], theme_id)].append(row)
    output: list[dict[str, Any]] = []
    for (sector, theme_id), group in sorted(grouped.items()):
        rates = [theme_rate(row, theme_id) for row in group]
        output.append(
            {
                "sector": sector,
                "theme_id": theme_id,
                "theme_label": THEME_LABELS[theme_id],
                "company_years": len(group),
                "presence_rate": _pct(
                    sum(1 for row in group if row["theme_counts"].get(theme_id, 0) > 0),
                    len(group),
                ),
                "mean_matches_per_10k_words": _mean(rates),
                "median_matches_per_10k_words": _median(rates),
            }
        )
    return output


def linguistic_year_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["year"]].append(row)
    output: list[dict[str, Any]] = []
    for year, group in sorted(grouped.items()):
        record: dict[str, Any] = {
            "year": year,
            "company_years": len(group),
            "mean_word_count": _mean([row["word_count"] for row in group]),
            "median_word_count": _median([row["word_count"] for row in group]),
        }
        for field in LINGUISTIC_RATE_FIELDS:
            record[f"mean_{field}"] = _mean(
                [float(row["linguistic_metrics"].get(field, 0)) for row in group]
            )
        output.append(record)
    return output


def sector_linguistic_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["sector"]].append(row)
    output: list[dict[str, Any]] = []
    for sector, group in sorted(grouped.items()):
        record: dict[str, Any] = {
            "sector": sector,
            "company_years": len(group),
            "mean_word_count": _mean([row["word_count"] for row in group]),
            "median_word_count": _median([row["word_count"] for row in group]),
        }
        for field in LINGUISTIC_RATE_FIELDS:
            record[f"mean_{field}"] = _mean(
                [float(row["linguistic_metrics"].get(field, 0)) for row in group]
            )
        output.append(record)
    return output


def company_theme_trends(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for theme_id in THEME_LABELS:
            grouped[(row["ticker"], theme_id)].append(row)
    output: list[dict[str, Any]] = []
    for (ticker, theme_id), group in sorted(grouped.items()):
        by_year = {row["year"]: theme_rate(row, theme_id) for row in group}
        if len(by_year) < 2:
            continue
        first_year = min(by_year)
        last_year = max(by_year)
        output.append(
            {
                "ticker": ticker,
                "company_name": group[0]["company_name"],
                "sector": group[0]["sector"],
                "theme_id": theme_id,
                "theme_label": THEME_LABELS[theme_id],
                "first_year": first_year,
                "last_year": last_year,
                "first_rate_per_10k_words": round(by_year[first_year], 6),
                "last_rate_per_10k_words": round(by_year[last_year], 6),
                "change_per_10k_words": round(by_year[last_year] - by_year[first_year], 6),
                "observed_years": len(by_year),
            }
        )
    return output


def adjacent_theme_shifts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for theme_id in THEME_LABELS:
            grouped[(row["ticker"], theme_id)].append(row)
    output: list[dict[str, Any]] = []
    for (ticker, theme_id), group in grouped.items():
        ordered = sorted(group, key=lambda row: row["year"])
        for prior, current in zip(ordered, ordered[1:], strict=False):
            prior_rate = theme_rate(prior, theme_id)
            current_rate = theme_rate(current, theme_id)
            output.append(
                {
                    "ticker": ticker,
                    "company_name": current["company_name"],
                    "sector": current["sector"],
                    "theme_id": theme_id,
                    "theme_label": THEME_LABELS[theme_id],
                    "prior_year": prior["year"],
                    "year": current["year"],
                    "prior_rate_per_10k_words": round(prior_rate, 6),
                    "rate_per_10k_words": round(current_rate, 6),
                    "change_per_10k_words": round(current_rate - prior_rate, 6),
                    "absolute_change_per_10k_words": round(abs(current_rate - prior_rate), 6),
                }
            )
    output.sort(key=lambda row: row["absolute_change_per_10k_words"], reverse=True)
    return output


def event_window_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for window_name, years in EVENT_WINDOWS.items():
        group = [row for row in rows if row["year"] in years]
        for theme_id in THEME_LABELS:
            rates = [theme_rate(row, theme_id) for row in group]
            output.append(
                {
                    "event_window": window_name,
                    "years": ",".join(str(year) for year in years),
                    "theme_id": theme_id,
                    "theme_label": THEME_LABELS[theme_id],
                    "company_years": len(group),
                    "mean_matches_per_10k_words": _mean(rates),
                    "presence_rate": _pct(
                        sum(1 for row in group if row["theme_counts"].get(theme_id, 0) > 0),
                        len(group),
                    ),
                }
            )
    return output


def missing_summary(missing: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in missing:
        grouped[(row["ticker"], row["company_name"], row["sector"])].append(row)
    output = []
    for (ticker, company_name, sector), group in sorted(grouped.items()):
        output.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "sector": sector,
                "missing_years": ",".join(str(row["year"]) for row in group),
                "missing_count": len(group),
                "gap_reasons": "; ".join(sorted({row["gap_reason"] for row in group})),
            }
        )
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _top_theme_rows(rows: list[dict[str, Any]], key: str, limit: int = 5) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row[key], reverse=True)[:limit]


def build_summary_payload(
    *,
    collected: list[dict[str, Any]],
    missing: list[dict[str, str]],
    theme_year: list[dict[str, Any]],
    theme_sector: list[dict[str, Any]],
    linguistic_year: list[dict[str, Any]],
    company_trends: list[dict[str, Any]],
    adjacent_shifts: list[dict[str, Any]],
    event_windows: list[dict[str, Any]],
) -> dict[str, Any]:
    overall_theme_totals = []
    for theme_id, label in THEME_LABELS.items():
        rates = [theme_rate(row, theme_id) for row in collected]
        overall_theme_totals.append(
            {
                "theme_id": theme_id,
                "theme_label": label,
                "mean_matches_per_10k_words": _mean(rates),
                "presence_rate": _pct(
                    sum(1 for row in collected if row["theme_counts"].get(theme_id, 0) > 0),
                    len(collected),
                ),
            }
        )
    overall_theme_totals.sort(key=lambda row: row["mean_matches_per_10k_words"], reverse=True)
    sector_leaders = []
    sectors = sorted({row["sector"] for row in theme_sector})
    for sector in sectors:
        sector_rows = [row for row in theme_sector if row["sector"] == sector]
        sector_leaders.append(
            {
                "sector": sector,
                "leading_themes": sorted(
                    sector_rows,
                    key=lambda row: row["mean_matches_per_10k_words"],
                    reverse=True,
                )[:4],
            }
        )
    event_lookup: dict[str, dict[str, float]] = defaultdict(dict)
    for row in event_windows:
        event_lookup[row["theme_id"]][row["event_window"]] = row["mean_matches_per_10k_words"]
    event_window_changes = []
    for theme_id, label in THEME_LABELS.items():
        pre = event_lookup[theme_id].get("pre_2020", 0.0)
        window = event_lookup[theme_id].get("covid_dei_governance_window", 0.0)
        post = event_lookup[theme_id].get("post_2021", 0.0)
        event_window_changes.append(
            {
                "theme_id": theme_id,
                "theme_label": label,
                "pre_2020_rate": pre,
                "covid_dei_governance_window_rate": window,
                "post_2021_rate": post,
                "window_minus_pre": round(window - pre, 6),
                "post_minus_pre": round(post - pre, 6),
            }
        )
    event_window_changes.sort(key=lambda row: row["window_minus_pre"], reverse=True)
    return {
        "method": (
            "Deterministic theme and linguistic analysis plus open-source exploratory "
            "model checks; no paid API or closed LLM used."
        ),
        "document_type": "SEC DEF 14A proxy statement",
        "collected_rows": len(collected),
        "missing_rows": len(missing),
        "coverage_rate": _pct(len(collected), len(collected) + len(missing)),
        "word_count": {
            "min": min(row["word_count"] for row in collected),
            "median": _median([row["word_count"] for row in collected]),
            "max": max(row["word_count"] for row in collected),
        },
        "top_overall_themes": overall_theme_totals,
        "sector_leading_themes": sector_leaders,
        "event_window_theme_changes": event_window_changes,
        "top_sector_theme_rates": _top_theme_rows(theme_sector, "mean_matches_per_10k_words", 10),
        "top_adjacent_theme_shifts": adjacent_shifts[:10],
        "largest_company_theme_increases": _top_theme_rows(
            company_trends,
            "change_per_10k_words",
            10,
        ),
        "linguistic_year_summary": linguistic_year,
        "event_window_summary": event_windows,
        "theme_year_rows": len(theme_year),
        "theme_sector_rows": len(theme_sector),
    }


def write_analysis_doc(path: Path, payload: dict[str, Any], missing: list[dict[str, Any]]) -> None:
    top_themes = "\n".join(
        "- {theme_label}: {mean_matches_per_10k_words:.2f} matches per 10k words; "
        "presence {presence_rate:.1%}".format(**row)
        for row in payload["top_overall_themes"]
    )
    top_shifts = "\n".join(
        (
            "- {ticker} {prior_year}-{year} {theme_label}: "
            "{change_per_10k_words:+.2f} per 10k words"
        ).format(**row)
        for row in payload["top_adjacent_theme_shifts"][:6]
    )
    missing_lines = "\n".join(
        "- {ticker}: {missing_years} ({gap_reasons})".format(**row) for row in missing
    )
    sector_lines = "\n".join(
        "- {sector}: {themes}".format(
            sector=row["sector"],
            themes=", ".join(
                "{theme_label} ({mean_matches_per_10k_words:.1f})".format(**theme)
                for theme in row["leading_themes"]
            ),
        )
        for row in payload["sector_leading_themes"]
    )
    event_lines = "\n".join(
        (
            "- {theme_label}: pre-2020 {pre_2020_rate:.2f}, 2020-2021 "
            "{covid_dei_governance_window_rate:.2f}, post-2021 {post_2021_rate:.2f}"
        ).format(**row)
        for row in payload["event_window_theme_changes"][:6]
    )
    year_lines = "\n".join(
        "- {year}: commitment {mean_commitment_rate_per_100_words:.3f}, "
        "action/evidence {mean_action_or_evidence_rate_per_100_words:.3f}, "
        "stakeholder {mean_stakeholder_rate_per_100_words:.3f}".format(**row)
        for row in payload["linguistic_year_summary"]
    )
    text = f"""# Part 2 Text Mining Analysis

## Method

This analysis uses deterministic text mining only. No paid API, closed model, or external LLM was
used. Theme analysis reuses the Part 1-compatible keyword taxonomy, and all theme rates are
normalized as matches per 10,000 words so long proxy statements do not dominate raw counts.

The analysis is based on {payload["collected_rows"]} collected SEC `DEF 14A` proxy statements out
of 450 target company-years, for {payload["coverage_rate"]:.2%} coverage. Missing rows remain
explicitly coded and are not imputed.

## Overall Theme Emphasis

{top_themes}

Proxy statements naturally emphasize governance, leadership, accountability, shareholders, and
performance. These results should therefore be interpreted as disclosed proxy priorities, not as
direct evidence of actual organizational behavior.

## Language Over Time

{year_lines}

The yearly linguistic indicators provide descriptive signals about disclosure style. They support
within-company and cross-year comparison, but they should not be read causally without document
section review.

## Cross-Sector Variation

{sector_lines}

The sector pattern is consistent with the document type. Consumer discretionary, healthcare, and
financial firms show especially strong shareholder/performance language. Technology filings show
the highest normalized DEI language among sectors. Energy filings show the strongest environment
and sustainability rate, but employee/workplace language is still the sector's top category.

## Largest Adjacent-Year Theme Shifts

{top_shifts}

Large adjacent-year changes are candidates for qualitative review. They may reflect genuine changes
in emphasis, new disclosure rules, document restructuring, mergers, or changes in proxy templates.

## External Event Window

The event-window table compares pre-2020 filings, the 2020-2021 COVID/DEI/governance disclosure
window, and 2022-2024 post-window filings. This is framed as cautious temporal comparison rather
than causal identification.

{event_lines}

## Coverage Gaps

{missing_lines}

These gaps should be carried into Part 3 as missing Part 2 observations, not zero alignment.
"""
    path.write_text(text, encoding="utf-8")


def write_final_summary_doc(
    path: Path,
    payload: dict[str, Any],
    missing: list[dict[str, Any]],
) -> None:
    top_theme_text = "; ".join(
        "{theme_label} ({mean_matches_per_10k_words:.1f}/10k)".format(**row)
        for row in payload["top_overall_themes"][:4]
    )
    missing_text = "; ".join(
        "{ticker}: {missing_years}".format(**row) for row in missing
    )
    sector_text = "\n".join(
        "- {sector}: {theme_label}".format(
            sector=row["sector"],
            theme_label=row["leading_themes"][0]["theme_label"],
        )
        for row in payload["sector_leading_themes"]
    )
    event_text = "\n".join(
        (
            "- {theme_label}: {window_minus_pre:+.2f} matches per 10k words "
            "in 2020-2021 versus pre-2020"
        ).format(**row)
        for row in payload["event_window_theme_changes"][:5]
    )
    text = f"""# Part 2 Summary

Part 2 uses SEC `DEF 14A` proxy statements as the single lived-values disclosure type. The full
run covers {payload["collected_rows"]} of 450 company-years ({payload["coverage_rate"]:.2%}).
The 16 missing rows remain explicitly coded and are not imputed.

The text-mining analysis uses deterministic, free, reproducible methods only: Part 1-compatible
theme matching, phrase evidence, normalized rates per 10,000 words, and descriptive linguistic
metrics. No paid API, closed model, or external LLM was used.

## Main Findings

The most prominent normalized themes are {top_theme_text}. This pattern is expected for proxy
statements, which are shareholder-facing governance documents. The results therefore measure
disclosed proxy priorities rather than direct lived behavior.

## Cross-Sector Pattern

{sector_text}

## Time and Event-Window Pattern

The 2020-2021 window shows higher normalized emphasis than the pre-2020 period for several themes:

{event_text}

These are descriptive shifts, not causal estimates. They are plausible candidates for qualitative
review because proxy disclosures changed during the COVID, workforce, DEI, and governance
attention cycle.

## Coverage Gaps

Missing rows: {missing_text}. These rows should remain missing in Part 3 alignment calculations
rather than being treated as zero disclosure emphasis.
"""
    path.write_text(text, encoding="utf-8")


def run_text_mining(dataset: Path, output_dir: Path, analysis_doc: Path) -> dict[str, Any]:
    collected, missing = read_dataset(dataset)
    theme_year = theme_year_summary(collected)
    theme_sector = theme_sector_summary(collected)
    linguistic_year = linguistic_year_summary(collected)
    sector_linguistic = sector_linguistic_summary(collected)
    company_trends = company_theme_trends(collected)
    adjacent_shifts = adjacent_theme_shifts(collected)
    event_windows = event_window_summary(collected)
    missing_rows = missing_summary(missing)

    write_csv(output_dir / "theme_year_summary.csv", theme_year)
    write_csv(output_dir / "theme_sector_summary.csv", theme_sector)
    write_csv(output_dir / "linguistic_year_summary.csv", linguistic_year)
    write_csv(output_dir / "sector_linguistic_summary.csv", sector_linguistic)
    write_csv(output_dir / "company_theme_trends.csv", company_trends)
    write_csv(output_dir / "top_adjacent_theme_shifts.csv", adjacent_shifts[:250])
    write_csv(output_dir / "event_window_summary.csv", event_windows)
    write_csv(output_dir / "missing_summary.csv", missing_rows)

    payload = build_summary_payload(
        collected=collected,
        missing=missing,
        theme_year=theme_year,
        theme_sector=theme_sector,
        linguistic_year=linguistic_year,
        company_trends=company_trends,
        adjacent_shifts=adjacent_shifts,
        event_windows=event_windows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "text_mining_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_analysis_doc(analysis_doc, payload, missing_rows)
    write_final_summary_doc(DEFAULT_SUMMARY_DOC, payload, missing_rows)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic Part 2 text-mining analysis.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--analysis-doc", type=Path, default=DEFAULT_ANALYSIS_DOC)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    payload = run_text_mining(args.dataset, args.output_dir, args.analysis_doc)
    print(
        json.dumps(
            {
                "collected_rows": payload["collected_rows"],
                "missing_rows": payload["missing_rows"],
                "coverage_rate": payload["coverage_rate"],
                "output_dir": str(args.output_dir),
                "analysis_doc": str(args.analysis_doc),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
