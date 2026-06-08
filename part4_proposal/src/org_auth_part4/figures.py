"""Generate Part 4 figures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from org_auth_part4.constants import (
    DIAGNOSTICS_OUTPUT,
    FIGURE_DIR,
    QUADRANT_FIGURE,
    SCATTER_FIGURE,
    SECTION_COMPOSITION_FIGURE,
    SECTION_FIGURE,
    SECTION_OUTPUT,
    SECTION_SUMMARY_OUTPUT,
    SECTION_THEME_HEATMAP_FIGURE,
    TERCILE_FIGURE,
    THEME_SEMANTIC_FIGURE,
    THEME_SEMANTIC_GAP_FIGURE,
    THEME_SEMANTIC_OUTPUT,
    THEME_SEMANTIC_SUMMARY_OUTPUT,
)

SECTION_LABELS = {
    "governance_board": "governance / board",
    "meeting_voting": "meeting / voting",
    "human_capital_values": "human capital / values",
    "shareholder_proposals": "shareholder proposals",
    "ownership": "ownership",
    "legal_other": "legal / other",
    "compensation": "compensation",
    "other": "other",
    "audit": "audit",
}

THEME_LABELS = {
    "customers_and_service": "customers / service",
    "employees_and_workplace": "employees / workplace",
    "innovation_and_excellence": "innovation / excellence",
    "integrity_and_ethics": "integrity / ethics",
    "diversity_equity_and_inclusion": "DEI",
    "social_impact_and_community": "social impact",
    "environment_and_sustainability": "environment",
    "health_safety_and_wellbeing": "health / safety",
    "shareholders_and_performance": "shareholders / performance",
    "leadership_and_accountability": "leadership / accountability",
    "collaboration_and_partnership": "collaboration",
    "purpose_and_identity": "purpose / identity",
}


def write_figures(diagnostics_path: Path = DIAGNOSTICS_OUTPUT) -> dict[str, str]:
    """Write the Part 4 diagnostic figures."""

    frame = pd.read_csv(diagnostics_path)
    scored = frame.dropna(subset=["proxy_genre_pressure", "authenticity_index"])
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    # The median lines turn the scatter into a diagnostic quadrant view without changing the
    # underlying continuous values used in the correlation/regression summaries.
    plt.scatter(
        scored["proxy_genre_pressure"],
        scored["authenticity_index"],
        alpha=0.68,
        s=34,
        color="#2f6f8f",
        edgecolors="white",
        linewidths=0.4,
    )
    plt.axhline(scored["authenticity_index"].median(), color="#9a3d3f", linewidth=1.4)
    plt.axvline(scored["proxy_genre_pressure"].median(), color="#616161", linewidth=1.4)
    plt.xlabel("Proxy genre pressure")
    plt.ylabel("Authenticity index")
    plt.title("Proxy genre pressure vs. authenticity index")
    plt.tight_layout()
    plt.savefig(SCATTER_FIGURE, dpi=200)
    plt.close()

    tercile = (
        scored.dropna(subset=["genre_pressure_tercile"])
        .groupby("genre_pressure_tercile", sort=False)["authenticity_index"]
        .agg(["mean", "median", "count"])
        .reindex(["low", "medium", "high"])
    )
    plt.figure(figsize=(7, 5))
    bars = plt.bar(
        tercile.index,
        tercile["mean"],
        color=["#6b9e78", "#d2a24c", "#9d5c63"],
        edgecolor="white",
    )
    for bar, count in zip(bars, tercile["count"], strict=True):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.8,
            f"n={int(count)}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.ylabel("Mean authenticity index")
    plt.xlabel("Proxy genre pressure tercile")
    plt.title("Authenticity by proxy genre pressure")
    plt.ylim(0, max(tercile["mean"].max() + 8, 10))
    plt.tight_layout()
    plt.savefig(TERCILE_FIGURE, dpi=200)
    plt.close()

    quadrant = (
        scored.dropna(subset=["keyword_semantic_quadrant"])
        .groupby("keyword_semantic_quadrant", sort=True)["proxy_genre_pressure"]
        .mean()
        .sort_values()
    )
    plt.figure(figsize=(8, 5))
    plt.barh(quadrant.index, quadrant.values, color="#5f7f9c", edgecolor="white")
    plt.xlabel("Mean proxy genre pressure")
    plt.ylabel("Keyword-semantic quadrant")
    plt.title("Genre pressure by keyword-semantic quadrant")
    plt.tight_layout()
    plt.savefig(QUADRANT_FIGURE, dpi=200)
    plt.close()

    if SECTION_SUMMARY_OUTPUT.exists():
        section = pd.read_csv(SECTION_SUMMARY_OUTPUT).head(8)
        plt.figure(figsize=(9, 5))
        plt.barh(
            section["section_family"],
            section["total_theme_matches"],
            color="#7a8f5a",
            edgecolor="white",
        )
        plt.xlabel("Total values-theme matches")
        plt.ylabel("Proxy section family")
        plt.title("Where proxy theme evidence appears")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(SECTION_FIGURE, dpi=200)
        plt.close()

    if SECTION_OUTPUT.exists():
        sections = pd.read_csv(SECTION_OUTPUT)
        theme_columns = [column for column in sections.columns if column.startswith("theme_")]
        theme_columns = [column for column in theme_columns if column.endswith("_count")]
        parsed = sections[sections["section_status"] == "parsed"].copy()
        heatmap = parsed.groupby("section_family")[theme_columns].sum()
        heatmap.columns = [
            column.removeprefix("theme_").removesuffix("_count") for column in heatmap.columns
        ]
        top_families = (
            parsed.groupby("section_family")["total_theme_matches"]
            .sum()
            .sort_values(ascending=False)
            .head(8)
            .index
        )
        heatmap = heatmap.loc[top_families]
        row_totals = heatmap.sum(axis=1).replace(0, pd.NA)
        # Row-normalization makes each heatmap row a section-family composition. This answers which
        # themes dominate a section family, not which family contributes the most raw evidence.
        heatmap_share = heatmap.div(row_totals, axis=0).fillna(0)

        plt.figure(figsize=(12, 6))
        sns.heatmap(
            heatmap_share,
            annot=True,
            cmap="viridis",
            fmt=".2f",
            linewidths=0.25,
            linecolor="white",
            cbar_kws={"label": "Theme share within section family"},
            annot_kws={"fontsize": 7},
        )
        plt.xlabel("Theme")
        plt.ylabel("Proxy section family")
        plt.title("Theme composition by proxy section family")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(SECTION_THEME_HEATMAP_FIGURE, dpi=200)
        plt.close()

        composition = (
            parsed.groupby("section_family")[["section_word_count", "total_theme_matches"]]
            .sum()
            .loc[top_families]
        )
        composition["theme_matches_per_1000_words"] = (
            1000 * composition["total_theme_matches"] / composition["section_word_count"]
        )
        plt.figure(figsize=(9, 5))
        # Bubble area encodes total theme evidence, while the axes separate section size from
        # values-theme density. This avoids reading raw governance volume as values density.
        plt.scatter(
            composition["section_word_count"],
            composition["theme_matches_per_1000_words"],
            s=composition["total_theme_matches"].clip(lower=1000) / 70,
            color="#547c75",
            alpha=0.78,
            edgecolors="white",
            linewidths=0.6,
        )
        for family, row in composition.iterrows():
            plt.text(
                row["section_word_count"],
                row["theme_matches_per_1000_words"],
                SECTION_LABELS.get(family, family.replace("_", " / ")),
                fontsize=8,
                ha="left",
                va="bottom",
            )
        legend_values = [10000, 50000, 100000]
        # The legend makes the otherwise implicit bubble-size encoding readable in the manuscript.
        legend_handles = [
            plt.scatter(
                [],
                [],
                s=value / 70,
                color="#547c75",
                alpha=0.78,
                edgecolors="white",
                linewidths=0.6,
                label=f"{value:,}",
            )
            for value in legend_values
            if value <= composition["total_theme_matches"].max()
        ]
        if legend_handles:
            plt.legend(
                handles=legend_handles,
                title="Total theme matches",
                loc="upper right",
                frameon=True,
            )
        plt.xlabel("Total parsed section words")
        plt.ylabel("Theme matches per 1,000 section words")
        plt.title("Section size and values-theme density")
        plt.tight_layout()
        plt.savefig(SECTION_COMPOSITION_FIGURE, dpi=200)
        plt.close()

    if THEME_SEMANTIC_SUMMARY_OUTPUT.exists():
        theme = pd.read_csv(THEME_SEMANTIC_SUMMARY_OUTPUT).sort_values(
            "mean_theme_semantic_similarity"
        )
        plt.figure(figsize=(9, 6))
        plt.barh(
            theme["theme_id"],
            theme["mean_theme_semantic_similarity"],
            color="#8a6f9c",
            edgecolor="white",
        )
        plt.xlabel("Mean theme-level semantic similarity")
        plt.ylabel("Theme")
        plt.title("Theme-level stated/proxy semantic similarity")
        plt.tight_layout()
        plt.savefig(THEME_SEMANTIC_FIGURE, dpi=200)
        plt.close()

    if THEME_SEMANTIC_OUTPUT.exists():
        theme_detail = pd.read_csv(THEME_SEMANTIC_OUTPUT)
        computed = theme_detail.dropna(subset=["theme_semantic_similarity"]).copy()
        theme_points = (
            computed.groupby("theme_id")
            .agg(
                mean_theme_semantic_similarity=("theme_semantic_similarity", "mean"),
                mean_theme_share_gap_abs=("theme_share_gap_abs", "mean"),
                computed_company_years=("theme_semantic_similarity", "size"),
            )
            .reset_index()
        )
        plt.figure(figsize=(9, 6))
        # This bubble plot separates two theme-level diagnostics: emphasis mismatch (x-axis) and
        # local same-theme semantic comparability (y-axis).
        plt.scatter(
            theme_points["mean_theme_share_gap_abs"],
            theme_points["mean_theme_semantic_similarity"],
            s=theme_points["computed_company_years"] * 2.0,
            color="#9c6b5f",
            alpha=0.78,
            edgecolors="white",
            linewidths=0.6,
        )
        for _, row in theme_points.iterrows():
            plt.text(
                row["mean_theme_share_gap_abs"],
                row["mean_theme_semantic_similarity"],
                THEME_LABELS.get(row["theme_id"], row["theme_id"].replace("_", " / ")),
                fontsize=7.5,
                ha="left",
                va="bottom",
            )
        x_min = theme_points["mean_theme_share_gap_abs"].min()
        x_max = theme_points["mean_theme_share_gap_abs"].max()
        plt.xlim(x_min - 0.005, x_max + 0.025)
        semantic_legend_values = [100, 200]
        # Bubble size represents how many company-year-theme comparisons support each theme point.
        semantic_handles = [
            plt.scatter(
                [],
                [],
                s=value * 2.0,
                color="#9c6b5f",
                alpha=0.78,
                edgecolors="white",
                linewidths=0.6,
                label=f"{value}",
            )
            for value in semantic_legend_values
            if value <= theme_points["computed_company_years"].max()
        ]
        if semantic_handles:
            plt.legend(
                handles=semantic_handles,
                title="Computed company-years",
                loc="lower right",
                frameon=True,
            )
        plt.xlabel("Mean absolute stated/disclosure theme-share gap")
        plt.ylabel("Mean theme-level semantic similarity")
        plt.title("Theme semantic similarity vs. emphasis gap")
        plt.tight_layout()
        plt.savefig(THEME_SEMANTIC_GAP_FIGURE, dpi=200)
        plt.close()

    return {
        str(SCATTER_FIGURE): "scatter",
        str(TERCILE_FIGURE): "bar",
        str(QUADRANT_FIGURE): "barh",
        str(SECTION_FIGURE): "barh" if SECTION_FIGURE.exists() else "missing",
        str(THEME_SEMANTIC_FIGURE): "barh" if THEME_SEMANTIC_FIGURE.exists() else "missing",
        str(SECTION_THEME_HEATMAP_FIGURE): "heatmap"
        if SECTION_THEME_HEATMAP_FIGURE.exists()
        else "missing",
        str(SECTION_COMPOSITION_FIGURE): "scatter"
        if SECTION_COMPOSITION_FIGURE.exists()
        else "missing",
        str(THEME_SEMANTIC_GAP_FIGURE): "scatter"
        if THEME_SEMANTIC_GAP_FIGURE.exists()
        else "missing",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, default=DIAGNOSTICS_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(write_figures(args.diagnostics), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
