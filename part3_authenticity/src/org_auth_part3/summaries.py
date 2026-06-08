"""Summary tables and robustness checks for the Part 3 index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from org_auth_part3.constants import (
    COMPANY_OUTPUT,
    DISTRIBUTION_OUTPUT,
    INDEX_OUTPUT,
    SECTOR_OUTPUT,
    SENSITIVITY_OUTPUT,
    YEAR_OUTPUT,
)


def scored_rows(index: pd.DataFrame) -> pd.DataFrame:
    """Return rows with a computed authenticity index."""

    return index[index["score_status"] == "scored"].copy()


def distribution_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Summarize overall score distribution and missingness."""

    scored = scored_rows(index)
    score = scored["authenticity_index"]
    return pd.DataFrame(
        [
            {
                "metric": "authenticity_index",
                "target_company_years": len(index),
                "scored_company_years": len(scored),
                "missing_company_years": len(index) - len(scored),
                "mean": round(score.mean(), 6),
                "median": round(score.median(), 6),
                "std": round(score.std(), 6),
                "min": round(score.min(), 6),
                "p10": round(score.quantile(0.10), 6),
                "p25": round(score.quantile(0.25), 6),
                "p75": round(score.quantile(0.75), 6),
                "p90": round(score.quantile(0.90), 6),
                "max": round(score.max(), 6),
            }
        ]
    )


def sector_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Summarize score distribution and missingness by sector."""

    rows = []
    for sector, group in index.groupby("sector", sort=True):
        scored = scored_rows(group)
        rows.append(
            {
                "sector": sector,
                "target_company_years": len(group),
                "scored_company_years": len(scored),
                "missing_company_years": len(group) - len(scored),
                "mean": round(scored["authenticity_index"].mean(), 6),
                "median": round(scored["authenticity_index"].median(), 6),
                "min": round(scored["authenticity_index"].min(), 6),
                "max": round(scored["authenticity_index"].max(), 6),
            }
        )
    return pd.DataFrame(rows)


def year_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Summarize score distribution and missingness by year."""

    rows = []
    for year, group in index.groupby("year", sort=True):
        scored = scored_rows(group)
        rows.append(
            {
                "year": int(year),
                "target_company_years": len(group),
                "scored_company_years": len(scored),
                "missing_company_years": len(group) - len(scored),
                "mean": round(scored["authenticity_index"].mean(), 6),
                "median": round(scored["authenticity_index"].median(), 6),
                "min": round(scored["authenticity_index"].min(), 6),
                "max": round(scored["authenticity_index"].max(), 6),
            }
        )
    return pd.DataFrame(rows)


def company_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Summarize score distribution and missingness by company."""

    rows = []
    for (ticker, company_name, sector), group in index.groupby(
        ["ticker", "company_name", "sector"], sort=True
    ):
        scored = scored_rows(group)
        rows.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "sector": sector,
                "target_years": len(group),
                "scored_years": len(scored),
                "missing_years": len(group) - len(scored),
                "mean_authenticity_index": round(scored["authenticity_index"].mean(), 6)
                if len(scored)
                else None,
                "median_authenticity_index": round(scored["authenticity_index"].median(), 6)
                if len(scored)
                else None,
            }
        )
    return pd.DataFrame(rows)


def sensitivity_summary(index: pd.DataFrame) -> pd.DataFrame:
    """Compare the primary score to alternative similarity specifications."""

    scored = scored_rows(index)
    metrics = [
        "cosine_alignment",
        "l1_alignment",
        "jaccard_theme_overlap",
        "semantic_text_similarity",
        "part2_word_count",
    ]
    rows = []
    for metric in metrics:
        metric_rows = scored[["authenticity_index", metric]].dropna()
        pearson = metric_rows["authenticity_index"].corr(
            metric_rows[metric],
            method="pearson",
        )
        spearman = metric_rows["authenticity_index"].corr(
            metric_rows[metric],
            method="spearman",
        )
        rows.append(
            {
                "comparison_metric": metric,
                "company_years": len(metric_rows),
                "pearson_correlation": round(float(pearson), 6),
                "spearman_correlation": round(float(spearman), 6),
            }
        )
    return pd.DataFrame(rows)


def write_summaries(index_path: Path = INDEX_OUTPUT) -> dict[str, str]:
    """Write all Part 3 summary outputs."""

    index = pd.read_csv(index_path)
    outputs = {
        DISTRIBUTION_OUTPUT: distribution_summary(index),
        SECTOR_OUTPUT: sector_summary(index),
        YEAR_OUTPUT: year_summary(index),
        COMPANY_OUTPUT: company_summary(index),
        SENSITIVITY_OUTPUT: sensitivity_summary(index),
    }
    for path, frame in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    return {str(path): str(len(frame)) for path, frame in outputs.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(write_summaries(args.index), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
