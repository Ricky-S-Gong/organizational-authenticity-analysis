"""Generate a compact Markdown results snapshot for Part 3.

This module turns saved CSV outputs into a lightweight Markdown appendix. It is deliberately
generated from data files rather than hand-written so the tables stay synchronized with the current
index, semantic robustness output, and quadrant diagnostics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from org_auth_part3.constants import (
    DISTRIBUTION_OUTPUT,
    DOCS_DIR,
    INDEX_OUTPUT,
    SECTOR_OUTPUT,
    SENSITIVITY_OUTPUT,
    YEAR_OUTPUT,
)

DEFAULT_OUTPUT = DOCS_DIR / "results_snapshot.md"


def _markdown_table(frame: pd.DataFrame) -> str:
    """Render a small pandas frame as a GitHub-flavored Markdown table."""

    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _metric_comparison_frame(index: pd.DataFrame) -> pd.DataFrame:
    """Return scored rows with keyword, semantic, and hybrid values on a shared scale."""

    scored = index[
        (index["score_status"] == "scored")
        & index["semantic_text_similarity"].notna()
    ].copy()
    scored["keyword"] = scored["authenticity_index"]
    scored["semantic"] = ((scored["semantic_text_similarity"] + 100) / 2).clip(0, 100)
    scored["hybrid"] = (scored["keyword"] + scored["semantic"]) / 2
    return scored


def metric_comparison_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Summarize keyword, semantic, and hybrid measures on a shared scale."""

    scored = _metric_comparison_frame(index)
    rows = []
    for metric in ["keyword", "semantic", "hybrid"]:
        values = scored[metric]
        rows.append(
            {
                "metric": metric,
                "company_years": len(values),
                "mean": round(values.mean(), 6),
                "median": round(values.median(), 6),
                "std": round(values.std(), 6),
                "min": round(values.min(), 6),
                "p25": round(values.quantile(0.25), 6),
                "p75": round(values.quantile(0.75), 6),
                "max": round(values.max(), 6),
            }
        )
    return pd.DataFrame(rows)


def metric_comparison_by_group(index: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Summarize keyword, semantic, and hybrid means by sector or year."""

    scored = _metric_comparison_frame(index)
    summary = (
        scored.groupby(group_column)[["keyword", "semantic", "hybrid"]]
        .mean()
        .round(6)
        .reset_index()
    )
    return summary


def keyword_semantic_quadrant_frame(index: pd.DataFrame) -> pd.DataFrame:
    """Classify scored rows by keyword/semantic quadrant."""

    scored = _metric_comparison_frame(index)
    keyword_median = scored["keyword"].median()
    semantic_median = scored["semantic"].median()
    # Median splits make the quadrant labels descriptive rather than normative: "high" means above
    # the current scored-sample median for that metric, not objectively good or bad behavior.
    scored["quadrant"] = "both_low"
    scored.loc[
        (scored["keyword"] >= keyword_median) & (scored["semantic"] >= semantic_median),
        "quadrant",
    ] = "both_high"
    scored.loc[
        (scored["keyword"] >= keyword_median) & (scored["semantic"] < semantic_median),
        "quadrant",
    ] = "keyword_high_only"
    scored.loc[
        (scored["keyword"] < keyword_median) & (scored["semantic"] >= semantic_median),
        "quadrant",
    ] = "semantic_high_only"
    scored["keyword_minus_semantic"] = scored["keyword"] - scored["semantic"]
    return scored


def keyword_semantic_quadrant_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Summarize the four keyword-semantic quadrants."""

    scored = keyword_semantic_quadrant_frame(index)
    return (
        scored.groupby("quadrant")
        .agg(
            company_years=("ticker", "size"),
            mean_keyword=("keyword", "mean"),
            mean_semantic=("semantic", "mean"),
            mean_hybrid=("hybrid", "mean"),
        )
        .round(6)
        .reset_index()
    )


def keyword_semantic_quadrant_cases(index: pd.DataFrame) -> pd.DataFrame:
    """Return one representative case for each keyword-semantic quadrant."""

    scored = keyword_semantic_quadrant_frame(index)
    columns = [
        "ticker",
        "company_name",
        "sector",
        "year",
        "keyword",
        "semantic",
        "hybrid",
        "keyword_minus_semantic",
    ]
    # Representative cases are selected to be visually legible and substantively interpretable:
    # strongest combined alignment, weakest combined alignment, and the largest metric divergences.
    cases = pd.concat(
        [
            scored[scored["quadrant"] == "both_high"]
            .assign(rank=scored["keyword"] + scored["semantic"])
            .sort_values("rank", ascending=False)
            .head(1),
            scored[scored["quadrant"] == "both_low"]
            .assign(rank=scored["keyword"] + scored["semantic"])
            .sort_values("rank")
            .head(1),
            scored[scored["quadrant"] == "keyword_high_only"]
            .sort_values("keyword_minus_semantic", ascending=False)
            .head(1),
            scored[scored["quadrant"] == "semantic_high_only"]
            .sort_values("keyword_minus_semantic")
            .head(1),
        ],
        ignore_index=True,
    )
    cases[["keyword", "semantic", "hybrid", "keyword_minus_semantic"]] = cases[
        ["keyword", "semantic", "hybrid", "keyword_minus_semantic"]
    ].round(6)
    return cases[["quadrant", *columns]]


def build_results_snapshot(
    distribution_path: Path = DISTRIBUTION_OUTPUT,
    sector_path: Path = SECTOR_OUTPUT,
    year_path: Path = YEAR_OUTPUT,
    sensitivity_path: Path = SENSITIVITY_OUTPUT,
    index_path: Path = INDEX_OUTPUT,
) -> str:
    """Build a small generated results snapshot from saved summary outputs."""

    distribution = pd.read_csv(distribution_path)
    sector = pd.read_csv(sector_path)
    year = pd.read_csv(year_path)
    sensitivity = pd.read_csv(sensitivity_path)
    index = pd.read_csv(index_path)
    metric_comparison = metric_comparison_summary(index)
    metric_sector = metric_comparison_by_group(index, "sector")
    metric_year = metric_comparison_by_group(index, "year")
    quadrant_summary = keyword_semantic_quadrant_summary(index)
    quadrant_cases = keyword_semantic_quadrant_cases(index)
    return "\n\n".join(
        [
            "# Part 3 Results Snapshot",
            "This file is generated from the Part 3 summary outputs.",
            "## Distribution",
            _markdown_table(distribution),
            "## Sector Summary",
            _markdown_table(sector),
            "## Year Summary",
            _markdown_table(year),
            "## Sensitivity Summary",
            _markdown_table(sensitivity),
            "## Keyword, Semantic, and Hybrid Summary",
            _markdown_table(metric_comparison),
            "## Keyword, Semantic, and Hybrid by Sector",
            _markdown_table(metric_sector),
            "## Keyword, Semantic, and Hybrid by Year",
            _markdown_table(metric_year),
            "## Keyword-Semantic Quadrant Summary",
            _markdown_table(quadrant_summary),
            "## Keyword-Semantic Quadrant Representative Cases",
            _markdown_table(quadrant_cases),
        ]
    )


def write_results_snapshot(output_path: Path = DEFAULT_OUTPUT) -> str:
    """Write the generated results snapshot."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = build_results_snapshot()
    output_path.write_text(text + "\n", encoding="utf-8")
    return str(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps({"output": write_results_snapshot(args.output)}, indent=2))


if __name__ == "__main__":
    main()
