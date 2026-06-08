"""Generate Part 3 score figures.

The figures are descriptive diagnostics for the written summary. They keep the primary keyword
index visually separate from supplementary semantic and hybrid standards while putting all three
on a comparable 0-100 scale where appropriate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from org_auth_part3.constants import FIGURES_DIR, INDEX_OUTPUT, SECTOR_OUTPUT, YEAR_OUTPUT


def _save(fig: plt.Figure, path: Path) -> None:
    """Save a Matplotlib figure with enough padding for long titles and labels."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def score_distribution(index: pd.DataFrame) -> plt.Figure:
    scored = index[index["score_status"] == "scored"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(scored["authenticity_index"], bins=20, color="#2f6f8f", edgecolor="white")
    ax.axvline(scored["authenticity_index"].median(), color="#c44e52", linewidth=2)
    ax.set_title("Organizational Authenticity Index Distribution")
    ax.set_xlabel("Authenticity index")
    ax.set_ylabel("Company-years")
    return fig


def sector_scores(sector: pd.DataFrame) -> plt.Figure:
    ordered = sector.sort_values("mean")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(ordered["sector"], ordered["mean"], color="#4c72b0")
    ax.set_title("Mean Authenticity Index by Sector")
    ax.set_xlabel("Mean authenticity index")
    ax.set_ylabel("")
    return fig


def year_scores(year: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(year["year"], year["mean"], marker="o", color="#55a868")
    ax.set_title("Mean Authenticity Index by Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean authenticity index")
    ax.set_xticks(year["year"])
    return fig


def metric_comparison_frame(index: pd.DataFrame) -> pd.DataFrame:
    """Return scored rows with comparable keyword, semantic, and hybrid measures."""

    scored = index[
        (index["score_status"] == "scored")
        & index["semantic_text_similarity"].notna()
    ].copy()
    # sentence-transformer cosine is stored on a -100 to 100 scale. The comparison plots rescale it
    # to 0-100 so readers can compare its level with the keyword index without changing the raw
    # semantic output.
    semantic_0_100 = ((scored["semantic_text_similarity"] + 100) / 2).clip(0, 100)
    scored["keyword"] = scored["authenticity_index"]
    scored["semantic"] = semantic_0_100
    scored["hybrid"] = (scored["keyword"] + scored["semantic"]) / 2
    return scored


def metric_comparison_distributions(index: pd.DataFrame) -> plt.Figure:
    """Compare keyword, semantic, and hybrid score distributions."""

    scored = metric_comparison_frame(index)
    metrics = [
        ("keyword", "Keyword theme overlap", "#2f6f8f"),
        ("semantic", "Semantic similarity", "#8a5a44"),
        ("hybrid", "Equal-weight hybrid", "#5b7f4f"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), sharey=True)
    for ax, (metric, title, color) in zip(axes, metrics, strict=True):
        ax.hist(scored[metric], bins=18, color=color, edgecolor="white")
        ax.axvline(scored[metric].median(), color="#202020", linewidth=1.6)
        ax.set_title(title)
        ax.set_xlabel("Score on comparable 0-100 scale")
        ax.set_xlim(0, 100)
    axes[0].set_ylabel("Company-years")
    fig.suptitle("Keyword, Semantic, and Hybrid Alignment Distributions", y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return fig


def metric_comparison_sector(index: pd.DataFrame) -> plt.Figure:
    """Compare keyword, semantic, and hybrid sector means."""

    scored = metric_comparison_frame(index)
    summary = (
        scored.groupby("sector")[["keyword", "semantic", "hybrid"]]
        .mean()
        .sort_values("keyword")
    )
    colors = ["#2f6f8f", "#8a5a44", "#5b7f4f"]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    summary.plot(kind="bar", ax=ax, color=colors, width=0.78)
    ax.set_title("Mean Alignment by Sector Across Three Standards")
    ax.set_xlabel("")
    ax.set_ylabel("Mean score on comparable 0-100 scale")
    ax.set_ylim(0, 100)
    ax.legend(["Keyword", "Semantic", "Hybrid"], frameon=False)
    ax.tick_params(axis="x", rotation=30)
    return fig


def metric_comparison_year(index: pd.DataFrame) -> plt.Figure:
    """Compare keyword, semantic, and hybrid year means."""

    scored = metric_comparison_frame(index)
    summary = scored.groupby("year")[["keyword", "semantic", "hybrid"]].mean()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(summary.index, summary["keyword"], marker="o", color="#2f6f8f", label="Keyword")
    ax.plot(summary.index, summary["semantic"], marker="s", color="#8a5a44", label="Semantic")
    ax.plot(summary.index, summary["hybrid"], marker="^", color="#5b7f4f", label="Hybrid")
    ax.set_title("Mean Alignment by Year Across Three Standards")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean score on comparable 0-100 scale")
    ax.set_ylim(0, 100)
    ax.set_xticks(summary.index)
    ax.legend(frameon=False)
    return fig


def keyword_semantic_scatter(index: pd.DataFrame) -> plt.Figure:
    """Plot keyword alignment against semantic similarity by quadrant."""

    scored = metric_comparison_frame(index)
    keyword_median = scored["keyword"].median()
    semantic_median = scored["semantic"].median()
    high_keyword = scored["keyword"] >= keyword_median
    high_semantic = scored["semantic"] >= semantic_median
    scored["quadrant"] = "Both low"
    scored.loc[high_keyword & high_semantic, "quadrant"] = "Both high"
    scored.loc[high_keyword & ~high_semantic, "quadrant"] = "Keyword high only"
    scored.loc[~high_keyword & high_semantic, "quadrant"] = "Semantic high only"

    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    colors = {
        "Both high": "#3f7f4f",
        "Both low": "#6f6f6f",
        "Keyword high only": "#2f6f8f",
        "Semantic high only": "#8a5a44",
    }
    for quadrant, group in scored.groupby("quadrant", sort=False):
        ax.scatter(
            group["keyword"],
            group["semantic"],
            s=42,
            alpha=0.72,
            color=colors[quadrant],
            edgecolor="white",
            linewidth=0.35,
            label=f"{quadrant} (n={len(group)})",
        )
    ax.axvline(keyword_median, color="#2f2f2f", linewidth=1.2, linestyle="--")
    ax.axhline(semantic_median, color="#2f2f2f", linewidth=1.2, linestyle="--")

    # Label one representative case per quadrant. These annotations connect the plot to the
    # qualitative audit notes without trying to label all 328 points.
    scored["quadrant_rank"] = scored["keyword"] + scored["semantic"]
    labels = [
        scored[scored["quadrant"] == "Both high"].sort_values("quadrant_rank").tail(1),
        scored[scored["quadrant"] == "Both low"].sort_values("quadrant_rank").head(1),
        scored[scored["quadrant"] == "Keyword high only"]
        .assign(divergence=scored["keyword"] - scored["semantic"])
        .sort_values("divergence", ascending=False)
        .head(1),
        scored[scored["quadrant"] == "Semantic high only"]
        .assign(divergence=scored["semantic"] - scored["keyword"])
        .sort_values("divergence", ascending=False)
        .head(1),
    ]
    labeled = pd.concat(labels, ignore_index=True)
    offsets = [(10, 8), (10, -12), (10, 12), (10, 8)]
    for row, offset in zip(labeled.itertuples(index=False), offsets, strict=True):
        ax.annotate(
            f"{row.ticker} {int(row.year)}",
            (row.keyword, row.semantic),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            arrowprops={"arrowstyle": "-", "color": "#555555", "linewidth": 0.55},
        )

    ax.set_title("Keyword Alignment vs Semantic Similarity")
    ax.set_xlabel("Keyword theme overlap index")
    ax.set_ylabel("Semantic similarity on comparable 0-100 scale")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    return fig


def write_figures(
    index_path: Path = INDEX_OUTPUT,
    sector_path: Path = SECTOR_OUTPUT,
    year_path: Path = YEAR_OUTPUT,
    output_dir: Path = FIGURES_DIR,
) -> dict[str, str]:
    """Write PNG and SVG figures for Part 3."""

    index = pd.read_csv(index_path)
    sector = pd.read_csv(sector_path)
    year = pd.read_csv(year_path)
    figures = {
        "score_distribution": score_distribution(index),
        "sector_scores": sector_scores(sector),
        "year_scores": year_scores(year),
        "metric_comparison_distributions": metric_comparison_distributions(index),
        "metric_comparison_sector": metric_comparison_sector(index),
        "metric_comparison_year": metric_comparison_year(index),
        "keyword_semantic_scatter": keyword_semantic_scatter(index),
    }
    outputs: dict[str, str] = {}
    rebuilders = {
        "score_distribution": lambda: score_distribution(index),
        "sector_scores": lambda: sector_scores(sector),
        "year_scores": lambda: year_scores(year),
        "metric_comparison_distributions": lambda: metric_comparison_distributions(index),
        "metric_comparison_sector": lambda: metric_comparison_sector(index),
        "metric_comparison_year": lambda: metric_comparison_year(index),
        "keyword_semantic_scatter": lambda: keyword_semantic_scatter(index),
    }
    for name, fig in figures.items():
        png = output_dir / f"{name}.png"
        svg = output_dir / f"{name}.svg"
        _save(fig, png)
        # Rebuild the figure for SVG because _save closes the original.
        rebuilt = rebuilders[name]()
        _save(rebuilt, svg)
        outputs[name] = str(png)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX_OUTPUT)
    parser.add_argument("--sector", type=Path, default=SECTOR_OUTPUT)
    parser.add_argument("--year", type=Path, default=YEAR_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=FIGURES_DIR)
    args = parser.parse_args()
    print(
        json.dumps(
            write_figures(args.index, args.sector, args.year, args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
