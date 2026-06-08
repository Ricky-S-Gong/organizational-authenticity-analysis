"""Generate dependency-free SVG figures for Part 2 text-mining outputs."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path
from typing import Any

from org_auth_part2.targets import PART2_ROOT
from org_auth_part2.text_mining import DEFAULT_OUTPUT_DIR

DEFAULT_FIGURE_DIR = PART2_ROOT / "outputs/text_mining/figures"

COLORS = (
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#db2777",
    "#65a30d",
    "#7c3aed",
    "#ca8a04",
    "#0f766e",
    "#475569",
)

TONE_FIELDS = (
    ("mean_first_person_plural_rate_per_100_words", "Collective voice"),
    ("mean_commitment_rate_per_100_words", "Commitment"),
    ("mean_aspiration_rate_per_100_words", "Aspirational"),
    ("mean_action_or_evidence_rate_per_100_words", "Action/evidence"),
    ("mean_stakeholder_rate_per_100_words", "Stakeholder orientation"),
)

STYLE_FIELDS = (
    ("mean_average_sentence_length", "Avg sentence length"),
    ("mean_quantified_claim_count", "Quantified claims"),
)

DOCUMENT_LENGTH_FIELDS = (
    ("mean_word_count", "Mean word count"),
    ("median_word_count", "Median word count"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a saved analysis CSV into dictionaries for plotting."""

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _scale(value: float, domain: tuple[float, float], range_: tuple[float, float]) -> float:
    """Linearly map a data value into SVG coordinate space."""

    low, high = domain
    start, end = range_
    if high == low:
        return (start + end) / 2
    return start + ((value - low) / (high - low)) * (end - start)


def _text(x: float, y: float, value: str, *, size: int = 12, anchor: str = "start") -> str:
    """Return an escaped SVG text element."""

    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'font-family="Arial, sans-serif" text-anchor="{anchor}" fill="#111827">'
        f"{html.escape(value)}</text>"
    )


def _axis_line(x1: float, y1: float, x2: float, y2: float) -> str:
    """Return a standard SVG axis or grid line."""

    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        'stroke="#6b7280" stroke-width="1"/>'
    )


def theme_over_time_svg(
    theme_year_rows: list[dict[str, str]],
    summary: dict[str, Any],
    *,
    width: int = 1280,
    height: int = 760,
    theme_ids: list[str] | None = None,
    title: str = "Part 2 Theme Emphasis Over Time",
    subtitle: str = (
        "All taxonomy themes; mean matches per 10,000 words among collected DEF 14A filings"
    ),
) -> str:
    """Build a multi-series SVG line chart for normalized theme rates."""

    top_theme_ids = theme_ids or [row["theme_id"] for row in summary["top_overall_themes"]]
    rows = [
        row for row in theme_year_rows if row["theme_id"] in top_theme_ids and row["year"].isdigit()
    ]
    years = sorted({int(row["year"]) for row in rows})
    max_rate = max(float(row["mean_matches_per_10k_words"]) for row in rows)
    left, right, top, bottom = 92, width - 370, 92, height - 90
    y_max = max_rate * 1.08
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(width / 2, 34, title, size=22, anchor="middle"),
        _text(width / 2, 70, subtitle, size=13, anchor="middle"),
        _axis_line(left, bottom, right, bottom),
        _axis_line(left, top, left, bottom),
    ]
    for tick in range(0, 6):
        value = y_max * tick / 5
        y = _scale(value, (0, y_max), (bottom, top))
        parts.append(_axis_line(left - 5, y, right, y))
        parts[-1] = parts[-1].replace('stroke="#6b7280"', 'stroke="#e5e7eb"')
        parts.append(_text(left - 12, y + 4, f"{value:.0f}", size=11, anchor="end"))
    for year in years:
        x = _scale(year, (min(years), max(years)), (left, right))
        parts.append(_axis_line(x, bottom, x, bottom + 5))
        parts.append(_text(x, bottom + 24, str(year), size=11, anchor="middle"))

    by_theme: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_theme.setdefault(row["theme_id"], []).append(row)
    for idx, theme_id in enumerate(top_theme_ids):
        color = COLORS[idx % len(COLORS)]
        series = sorted(by_theme[theme_id], key=lambda row: int(row["year"]))
        points = []
        for row in series:
            x = _scale(int(row["year"]), (min(years), max(years)), (left, right))
            y = _scale(float(row["mean_matches_per_10k_words"]), (0, y_max), (bottom, top))
            points.append((x, y))
        path = " ".join(
            ("M" if idx_point == 0 else "L") + f" {x:.1f} {y:.1f}"
            for idx_point, (x, y) in enumerate(points)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
        label = series[0]["theme_label"]
        legend_y = top + idx * 24
        parts.append(
            f'<rect x="{right + 34}" y="{legend_y - 10}" width="14" height="14" fill="{color}"/>'
        )
        parts.append(_text(right + 56, legend_y + 2, label, size=11))
    parts.append(
        _text(
            30,
            height - 24,
            "Generated from outputs/text_mining/theme_year_summary.csv",
            size=11,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def split_theme_ids_by_intensity(
    summary: dict[str, Any],
    *,
    threshold: float = 10.0,
) -> tuple[list[str], list[str]]:
    """Split themes into readable high- and low-intensity line charts."""

    high = [
        row["theme_id"]
        for row in summary["top_overall_themes"]
        if float(row["mean_matches_per_10k_words"]) >= threshold
    ]
    low = [
        row["theme_id"]
        for row in summary["top_overall_themes"]
        if float(row["mean_matches_per_10k_words"]) < threshold
    ]
    return high, low


def sector_heatmap_svg(
    theme_sector_rows: list[dict[str, str]],
    summary: dict[str, Any],
    *,
    width: int = 1480,
    height: int = 700,
) -> str:
    """Build a warm SVG heatmap of sector-level theme emphasis."""

    theme_ids = [row["theme_id"] for row in summary["top_overall_themes"]]
    sectors = sorted({row["sector"] for row in theme_sector_rows})
    lookup = {
        (row["sector"], row["theme_id"]): float(row["mean_matches_per_10k_words"])
        for row in theme_sector_rows
    }
    labels = {
        row["theme_id"]: row["theme_label"]
        for row in theme_sector_rows
        if row["theme_id"] in theme_ids
    }
    max_value = max(
        lookup.get((sector, theme_id), 0) for sector in sectors for theme_id in theme_ids
    )
    left, top = 230, 115
    cell_w, cell_h = 92, 68
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(30, 34, "Cross-Sector Theme Heatmap", size=22),
        _text(30, 56, "All taxonomy themes; mean matches per 10,000 words by sector", size=13),
    ]
    for col, theme_id in enumerate(theme_ids):
        x = left + col * cell_w + cell_w / 2
        words = labels[theme_id].replace(" and ", " & ").split()
        for offset, word in enumerate(words[:3]):
            parts.append(_text(x, top - 48 + offset * 13, word, size=10, anchor="middle"))
    for row_idx, sector in enumerate(sectors):
        y = top + row_idx * cell_h
        parts.append(_text(left - 16, y + cell_h / 2 + 4, sector, size=12, anchor="end"))
        for col, theme_id in enumerate(theme_ids):
            value = lookup.get((sector, theme_id), 0)
            intensity = _scale(value, (0, max_value), (0.12, 1.0))
            red = int(239 - intensity * 190)
            green = int(246 - intensity * 120)
            blue = int(255 - intensity * 40)
            x = left + col * cell_w
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" '
                f'rx="0" fill="rgb({red},{green},{blue})" stroke="#ffffff"/>'
            )
            parts.append(
                _text(
                    x + cell_w / 2 - 2,
                    y + cell_h / 2 + 4,
                    f"{value:.1f}",
                    size=12,
                    anchor="middle",
                )
            )
    parts.append(
        _text(
            30,
            height - 24,
            "Darker cells indicate higher normalized theme emphasis.",
            size=11,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def event_window_svg(
    summary: dict[str, Any],
    *,
    width: int = 980,
    height: int = 560,
) -> str:
    """Build an SVG bar chart for the 2020-2021 event-window comparison."""

    rows = summary["event_window_theme_changes"][:8]
    max_abs = max(abs(float(row["window_minus_pre"])) for row in rows)
    left, right, top, bottom = 300, width - 70, 70, height - 70
    zero_x = _scale(0, (-max_abs, max_abs), (left, right))
    bar_h = 28
    gap = 20
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(30, 34, "Part 2 2020-2021 Event-Window Theme Change", size=22),
        _text(30, 56, "Change in mean matches per 10,000 words versus pre-2020", size=13),
        _axis_line(zero_x, top - 10, zero_x, bottom),
    ]
    for idx, row in enumerate(rows):
        value = float(row["window_minus_pre"])
        y = top + idx * (bar_h + gap)
        x = _scale(min(0, value), (-max_abs, max_abs), (left, right))
        bar_w = abs(_scale(value, (-max_abs, max_abs), (left, right)) - zero_x)
        color = "#2563eb" if value >= 0 else "#dc2626"
        parts.append(_text(left - 18, y + 19, row["theme_label"], size=12, anchor="end"))
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" fill="{color}"/>'
        )
        label_x = x + bar_w + 8 if value >= 0 else x - 8
        anchor = "start" if value >= 0 else "end"
        parts.append(_text(label_x, y + 19, f"{value:+.2f}", size=12, anchor=anchor))
    parts.append(
        _text(
            30,
            height - 24,
            "Descriptive comparison only; not a causal estimate.",
            size=11,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def language_tone_over_time_svg(
    linguistic_year_rows: list[dict[str, str]],
    *,
    width: int = 1040,
    height: int = 620,
) -> str:
    """Build an indexed SVG line chart for lexical tone indicators."""

    years = sorted(int(row["year"]) for row in linguistic_year_rows if row["year"].isdigit())
    rows_by_year = {int(row["year"]): row for row in linguistic_year_rows}
    indexed: dict[str, dict[int, float]] = {}
    for field, _label in TONE_FIELDS:
        base = float(rows_by_year[min(years)][field])
        indexed[field] = {
            year: (float(rows_by_year[year][field]) / base) * 100 if base else 0 for year in years
        }
    max_rate = max(value for series in indexed.values() for value in series.values())
    min_rate = min(value for series in indexed.values() for value in series.values())
    left, right, top, bottom = 92, width - 260, 70, height - 90
    y_low = min(80, min_rate * 0.96)
    y_high = max_rate * 1.04
    if y_high <= y_low:
        y_high = y_low + 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(30, 34, "Part 2 Language and Tone Over Time", size=22),
        _text(30, 56, "Lexical tone indicators indexed to 2016 = 100", size=13),
        _axis_line(left, bottom, right, bottom),
        _axis_line(left, top, left, bottom),
    ]
    for tick in range(0, 6):
        value = y_low + (y_high - y_low) * tick / 5
        y = _scale(value, (y_low, y_high), (bottom, top))
        parts.append(
            _axis_line(left - 5, y, right, y).replace('stroke="#6b7280"', 'stroke="#e5e7eb"')
        )
        parts.append(_text(left - 12, y + 4, f"{value:.0f}", size=11, anchor="end"))
    for year in years:
        x = _scale(year, (min(years), max(years)), (left, right))
        parts.append(_axis_line(x, bottom, x, bottom + 5))
        parts.append(_text(x, bottom + 24, str(year), size=11, anchor="middle"))
    for idx, (field, label) in enumerate(TONE_FIELDS):
        color = COLORS[idx % len(COLORS)]
        points = []
        for year in years:
            x = _scale(year, (min(years), max(years)), (left, right))
            y = _scale(indexed[field][year], (y_low, y_high), (bottom, top))
            points.append((x, y))
        path = " ".join(
            ("M" if idx_point == 0 else "L") + f" {x:.1f} {y:.1f}"
            for idx_point, (x, y) in enumerate(points)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
        legend_y = top + idx * 26
        parts.append(
            f'<rect x="{right + 34}" y="{legend_y - 10}" width="14" height="14" fill="{color}"/>'
        )
        parts.append(_text(right + 56, legend_y + 2, label, size=12))
    parts.append(
        _text(
            30,
            height - 24,
            "Table values preserve raw rates per 100 words; the figure compares relative change.",
            size=11,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _indexed_line_svg(
    rows: list[dict[str, str]],
    fields: tuple[tuple[str, str], ...],
    *,
    title: str,
    subtitle: str,
    footer: str,
    width: int = 1040,
    height: int = 620,
) -> str:
    """Build a reusable indexed line chart for measures with different raw units."""

    years = sorted(int(row["year"]) for row in rows if row["year"].isdigit())
    rows_by_year = {int(row["year"]): row for row in rows}
    indexed: dict[str, dict[int, float]] = {}
    for field, _label in fields:
        base = float(rows_by_year[min(years)][field])
        indexed[field] = {
            year: (float(rows_by_year[year][field]) / base) * 100 if base else 0 for year in years
        }
    max_rate = max(value for series in indexed.values() for value in series.values())
    min_rate = min(value for series in indexed.values() for value in series.values())
    left, right, top, bottom = 92, width - 260, 70, height - 90
    y_low = min(80, min_rate * 0.96)
    y_high = max_rate * 1.04
    if y_high <= y_low:
        y_high = y_low + 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(width / 2, 34, title, size=22, anchor="middle"),
        _text(width / 2, 56, subtitle, size=13, anchor="middle"),
        _axis_line(left, bottom, right, bottom),
        _axis_line(left, top, left, bottom),
    ]
    for tick in range(0, 6):
        value = y_low + (y_high - y_low) * tick / 5
        y = _scale(value, (y_low, y_high), (bottom, top))
        parts.append(
            _axis_line(left - 5, y, right, y).replace('stroke="#6b7280"', 'stroke="#e5e7eb"')
        )
        parts.append(_text(left - 12, y + 4, f"{value:.0f}", size=11, anchor="end"))
    for year in years:
        x = _scale(year, (min(years), max(years)), (left, right))
        parts.append(_axis_line(x, bottom, x, bottom + 5))
        parts.append(_text(x, bottom + 24, str(year), size=11, anchor="middle"))
    for idx, (field, label) in enumerate(fields):
        color = COLORS[idx % len(COLORS)]
        points = []
        for year in years:
            x = _scale(year, (min(years), max(years)), (left, right))
            y = _scale(indexed[field][year], (y_low, y_high), (bottom, top))
            points.append((x, y))
        path = " ".join(
            ("M" if idx_point == 0 else "L") + f" {x:.1f} {y:.1f}"
            for idx_point, (x, y) in enumerate(points)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
        legend_y = top + idx * 26
        parts.append(
            f'<rect x="{right + 34}" y="{legend_y - 10}" width="14" height="14" fill="{color}"/>'
        )
        parts.append(_text(right + 56, legend_y + 2, label, size=12))
    parts.append(_text(30, height - 24, footer, size=11))
    parts.append("</svg>")
    return "\n".join(parts)


def language_style_over_time_svg(
    linguistic_year_rows: list[dict[str, str]],
) -> str:
    """Build the disclosure-style SVG using indexed sentence/number measures."""

    return _indexed_line_svg(
        linguistic_year_rows,
        STYLE_FIELDS,
        title="Part 2 Disclosure Style Over Time",
        subtitle="Sentence length and quantified claims indexed to 2016 = 100",
        footer="Table values preserve raw sentence-length and quantified-claim measures.",
    )


def document_length_over_time_svg(
    linguistic_year_rows: list[dict[str, str]],
) -> str:
    """Build the document-length SVG as interpretation context."""

    return _indexed_line_svg(
        linguistic_year_rows,
        DOCUMENT_LENGTH_FIELDS,
        title="Part 2 Document Length Over Time",
        subtitle="Mean and median proxy-statement word counts indexed to 2016 = 100",
        footer="Document length is tracked as disclosure context, not as tone itself.",
    )


def sector_tone_heatmap_svg(
    sector_linguistic_rows: list[dict[str, str]],
    *,
    width: int = 980,
    height: int = 560,
) -> str:
    """Build a sector tone heatmap with per-indicator color scaling."""

    field_ranges = {}
    for field, _label in TONE_FIELDS:
        values = [float(row[field]) for row in sector_linguistic_rows]
        field_ranges[field] = (min(values), max(values))
    left, top = 240, 110
    cell_w, cell_h = 145, 64
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(30, 34, "Part 2 Cross-Sector Language and Tone", size=22),
        _text(30, 56, "Lexical tone indicators per 100 words by sector", size=13),
    ]
    for col, (_field, label) in enumerate(TONE_FIELDS):
        x = left + col * cell_w + cell_w / 2
        for offset, word in enumerate(label.split()):
            parts.append(_text(x, top - 42 + offset * 14, word, size=11, anchor="middle"))
    for row_idx, row in enumerate(sector_linguistic_rows):
        y = top + row_idx * cell_h
        parts.append(_text(left - 16, y + cell_h / 2 + 4, row["sector"], size=12, anchor="end"))
        for col, (field, _label) in enumerate(TONE_FIELDS):
            value = float(row[field])
            intensity = _scale(value, field_ranges[field], (0.10, 1.0))
            red = int(255 - intensity * 105)
            green = int(247 - intensity * 150)
            blue = int(237 - intensity * 210)
            x = left + col * cell_w
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" '
                f'rx="0" fill="rgb({red},{green},{blue})" stroke="#ffffff"/>'
            )
            parts.append(
                _text(
                    x + cell_w / 2 - 2,
                    y + cell_h / 2 + 4,
                    f"{value:.3f}",
                    size=12,
                    anchor="middle",
                )
            )
    parts.append(
        _text(
            30,
            height - 24,
            "Darker cells indicate higher within-indicator sector rank; labels show raw rates.",
            size=11,
        )
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _try_load_plotting():
    """Import optional plotting dependencies and return graceful fallbacks."""

    try:
        os.environ.setdefault(
            "MPLCONFIGDIR",
            str(PART2_ROOT / "data/interim/matplotlib"),
        )
        import matplotlib.pyplot as plt  # type: ignore[import-not-found]
        import seaborn as sns  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return None, None
    sns.set_theme(style="whitegrid", context="talk")
    return plt, sns


def _save_theme_over_time_png(
    theme_year_rows: list[dict[str, str]],
    summary: dict[str, Any],
    figure_dir: Path,
    *,
    theme_ids: list[str] | None = None,
    filename: str = "theme_over_time.png",
    title: str = "Part 2 Theme Emphasis Over Time",
    subtitle: str = (
        "All taxonomy themes; mean matches per 10,000 words among collected DEF 14A filings"
    ),
) -> Path | None:
    """Save a PNG version of the theme-over-time line chart when plotting is available."""

    plt, _sns = _try_load_plotting()
    if plt is None:
        return None
    top_theme_ids = theme_ids or [row["theme_id"] for row in summary["top_overall_themes"]]
    rows = [row for row in theme_year_rows if row["theme_id"] in top_theme_ids]
    fig, ax = plt.subplots(figsize=(13.5, 7.6))
    for idx, theme_id in enumerate(top_theme_ids):
        series = sorted(
            [row for row in rows if row["theme_id"] == theme_id],
            key=lambda row: int(row["year"]),
        )
        ax.plot(
            [int(row["year"]) for row in series],
            [float(row["mean_matches_per_10k_words"]) for row in series],
            marker="o",
            linewidth=2.2,
            label=series[0]["theme_label"],
            color=COLORS[idx % len(COLORS)],
        )
    fig.suptitle(title, y=0.985, weight="bold", fontsize=20)
    fig.text(0.5, 0.915, subtitle, ha="center", fontsize=12)
    ax.set_ylabel("Mean matches per 10,000 words")
    ax.set_xlabel("Filing year")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    ax.set_position((0.07, 0.11, 0.74, 0.765))
    path = figure_dir / filename
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_sector_heatmap_png(
    theme_sector_rows: list[dict[str, str]],
    summary: dict[str, Any],
    figure_dir: Path,
) -> Path | None:
    """Save the cross-sector theme heatmap as a publication-friendly PNG."""

    plt, sns = _try_load_plotting()
    if plt is None or sns is None:
        return None
    theme_ids = [row["theme_id"] for row in summary["top_overall_themes"]]
    sectors = sorted({row["sector"] for row in theme_sector_rows})
    labels = {
        row["theme_id"]: row["theme_label"].replace(" and ", " & ") for row in theme_sector_rows
    }
    lookup = {
        (row["sector"], row["theme_id"]): float(row["mean_matches_per_10k_words"])
        for row in theme_sector_rows
    }
    matrix = [[lookup.get((sector, theme_id), 0.0) for theme_id in theme_ids] for sector in sectors]
    fig, ax = plt.subplots(figsize=(17, 8.8))
    sns.heatmap(
        matrix,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        xticklabels=[labels[theme_id] for theme_id in theme_ids],
        yticklabels=sectors,
        cbar_kws={"label": "Matches per 10,000 words"},
        ax=ax,
    )
    ax.set_title("Cross-Sector Theme Heatmap", pad=16, weight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels(
        [labels[theme_id] for theme_id in theme_ids],
        rotation=90,
        ha="center",
        va="top",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.46)
    path = figure_dir / "sector_theme_heatmap.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_event_window_png(summary: dict[str, Any], figure_dir: Path) -> Path | None:
    """Save the event-window comparison as a horizontal bar chart."""

    plt, _sns = _try_load_plotting()
    if plt is None:
        return None
    rows = list(reversed(summary["event_window_theme_changes"][:8]))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    values = [float(row["window_minus_pre"]) for row in rows]
    labels = [row["theme_label"] for row in rows]
    colors = ["#2563eb" if value >= 0 else "#dc2626" for value in values]
    ax.barh(labels, values, color=colors)
    ax.axvline(0, color="#111827", linewidth=1)
    ax.set_title("2020-2021 Event-Window Theme Change", pad=16, weight="bold")
    ax.set_xlabel("Change in matches per 10,000 words vs. pre-2020")
    for idx, value in enumerate(values):
        ax.text(
            value + (0.15 if value >= 0 else -0.15),
            idx,
            f"{value:+.2f}",
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=11,
        )
    fig.tight_layout()
    path = figure_dir / "event_window_theme_change.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_language_tone_over_time_png(
    linguistic_year_rows: list[dict[str, str]],
    figure_dir: Path,
) -> Path | None:
    """Save indexed lexical tone indicators as a PNG line chart."""

    plt, _sns = _try_load_plotting()
    if plt is None:
        return None
    rows = sorted(linguistic_year_rows, key=lambda row: int(row["year"]))
    base_row = rows[0]
    fig, ax = plt.subplots(figsize=(12, 7))
    for color, (field, label) in zip(COLORS, TONE_FIELDS, strict=False):
        base = float(base_row[field])
        ax.plot(
            [int(row["year"]) for row in rows],
            [(float(row[field]) / base) * 100 if base else 0 for row in rows],
            marker="o",
            linewidth=2.5,
            label=label,
            color=color,
        )
    fig.suptitle("Part 2 Language and Tone Over Time", y=0.985, weight="bold", fontsize=20)
    fig.text(
        0.5,
        0.915,
        "Lexical tone indicators indexed to 2016 = 100",
        ha="center",
        fontsize=12,
    )
    ax.set_ylabel("Index, 2016 = 100")
    ax.set_xlabel("Filing year")
    ax.axhline(100, color="#6b7280", linewidth=1, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    ax.set_position((0.07, 0.11, 0.74, 0.765))
    path = figure_dir / "language_tone_over_time.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_indexed_fields_png(
    rows: list[dict[str, str]],
    figure_dir: Path,
    fields: tuple[tuple[str, str], ...],
    *,
    filename: str,
    title: str,
    subtitle: str,
    footer: str,
) -> Path | None:
    """Save a generic indexed-fields PNG line chart."""

    plt, _sns = _try_load_plotting()
    if plt is None:
        return None
    sorted_rows = sorted(rows, key=lambda row: int(row["year"]))
    base_row = sorted_rows[0]
    fig, ax = plt.subplots(figsize=(12, 7))
    for idx, (field, label) in enumerate(fields):
        base = float(base_row[field])
        ax.plot(
            [int(row["year"]) for row in sorted_rows],
            [(float(row[field]) / base) * 100 if base else 0 for row in sorted_rows],
            marker="o",
            linewidth=2.5,
            label=label,
            color=COLORS[idx % len(COLORS)],
        )
    fig.suptitle(title, y=0.985, weight="bold", fontsize=20)
    fig.text(0.5, 0.915, subtitle, ha="center", fontsize=12)
    ax.set_ylabel("Index, 2016 = 100")
    ax.set_xlabel("Filing year")
    ax.axhline(100, color="#6b7280", linewidth=1, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    ax.text(0, -0.18, footer, transform=ax.transAxes, fontsize=10, color="#374151")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    ax.set_position((0.07, 0.11, 0.74, 0.765))
    path = figure_dir / filename
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def _save_language_style_over_time_png(
    linguistic_year_rows: list[dict[str, str]],
    figure_dir: Path,
) -> Path | None:
    """Save sentence-length and quantified-claim trends as a PNG."""

    return _save_indexed_fields_png(
        linguistic_year_rows,
        figure_dir,
        STYLE_FIELDS,
        filename="language_style_over_time.png",
        title="Part 2 Disclosure Style Over Time",
        subtitle="Sentence length and quantified claims indexed to 2016 = 100",
        footer="Table values preserve raw sentence-length and quantified-claim measures.",
    )


def _save_document_length_over_time_png(
    linguistic_year_rows: list[dict[str, str]],
    figure_dir: Path,
) -> Path | None:
    """Save mean and median document-length trends as a PNG."""

    return _save_indexed_fields_png(
        linguistic_year_rows,
        figure_dir,
        DOCUMENT_LENGTH_FIELDS,
        filename="document_length_over_time.png",
        title="Part 2 Document Length Over Time",
        subtitle="Mean and median proxy-statement word counts indexed to 2016 = 100",
        footer="Document length is tracked as disclosure context, not as tone itself.",
    )


def _save_sector_tone_heatmap_png(
    sector_linguistic_rows: list[dict[str, str]],
    figure_dir: Path,
) -> Path | None:
    """Save the sector-level language/tone heatmap as a PNG."""

    plt, sns = _try_load_plotting()
    if plt is None or sns is None:
        return None
    rows = sorted(sector_linguistic_rows, key=lambda row: row["sector"])
    raw_matrix = [[float(row[field]) for field, _label in TONE_FIELDS] for row in rows]
    color_matrix = []
    for row in rows:
        color_row = []
        for field, _label in TONE_FIELDS:
            values = [float(item[field]) for item in rows]
            low, high = min(values), max(values)
            value = float(row[field])
            color_row.append((value - low) / (high - low) if high != low else 0.5)
        color_matrix.append(color_row)
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    sns.heatmap(
        color_matrix,
        annot=raw_matrix,
        fmt=".3f",
        cmap="YlOrBr",
        xticklabels=[label for _field, label in TONE_FIELDS],
        yticklabels=[row["sector"] for row in rows],
        cbar_kws={"label": "Within-indicator relative intensity"},
        ax=ax,
    )
    ax.set_title("Part 2 Cross-Sector Language and Tone", pad=16, weight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels(
        [label for _field, label in TONE_FIELDS],
        rotation=90,
        ha="center",
        va="top",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.30)
    path = figure_dir / "sector_tone_heatmap.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def write_figures(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    figure_dir: Path = DEFAULT_FIGURE_DIR,
) -> list[Path]:
    """Write all SVG figures and optional PNG counterparts."""

    figure_dir.mkdir(parents=True, exist_ok=True)
    summary = json.loads((output_dir / "text_mining_summary.json").read_text(encoding="utf-8"))
    theme_year = read_csv(output_dir / "theme_year_summary.csv")
    theme_sector = read_csv(output_dir / "theme_sector_summary.csv")
    linguistic_year = read_csv(output_dir / "linguistic_year_summary.csv")
    sector_linguistic = read_csv(output_dir / "sector_linguistic_summary.csv")
    high_theme_ids, low_theme_ids = split_theme_ids_by_intensity(summary)
    figures = {
        "theme_over_time.svg": theme_over_time_svg(theme_year, summary),
        "theme_over_time_high.svg": theme_over_time_svg(
            theme_year,
            summary,
            theme_ids=high_theme_ids,
            title="Part 2 Theme Emphasis Over Time: Higher-Intensity Themes",
            subtitle="Themes with overall mean >= 10 matches per 10,000 words",
        ),
        "theme_over_time_low.svg": theme_over_time_svg(
            theme_year,
            summary,
            theme_ids=low_theme_ids,
            title="Part 2 Theme Emphasis Over Time: Lower-Intensity Themes",
            subtitle="Themes with overall mean < 10 matches per 10,000 words",
        ),
        "sector_theme_heatmap.svg": sector_heatmap_svg(theme_sector, summary),
        "event_window_theme_change.svg": event_window_svg(summary),
        "language_tone_over_time.svg": language_tone_over_time_svg(linguistic_year),
        "language_style_over_time.svg": language_style_over_time_svg(linguistic_year),
        "document_length_over_time.svg": document_length_over_time_svg(linguistic_year),
        "sector_tone_heatmap.svg": sector_tone_heatmap_svg(sector_linguistic),
    }
    paths = []
    for name, svg in figures.items():
        path = figure_dir / name
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
    for path in (
        _save_theme_over_time_png(theme_year, summary, figure_dir),
        _save_theme_over_time_png(
            theme_year,
            summary,
            figure_dir,
            theme_ids=high_theme_ids,
            filename="theme_over_time_high.png",
            title="Part 2 Theme Emphasis Over Time: Higher-Intensity Themes",
            subtitle="Themes with overall mean >= 10 matches per 10,000 words",
        ),
        _save_theme_over_time_png(
            theme_year,
            summary,
            figure_dir,
            theme_ids=low_theme_ids,
            filename="theme_over_time_low.png",
            title="Part 2 Theme Emphasis Over Time: Lower-Intensity Themes",
            subtitle="Themes with overall mean < 10 matches per 10,000 words",
        ),
        _save_sector_heatmap_png(theme_sector, summary, figure_dir),
        _save_event_window_png(summary, figure_dir),
        _save_language_tone_over_time_png(linguistic_year, figure_dir),
        _save_language_style_over_time_png(linguistic_year, figure_dir),
        _save_document_length_over_time_png(linguistic_year, figure_dir),
        _save_sector_tone_heatmap_png(sector_linguistic, figure_dir),
    ):
        if path is not None:
            paths.append(path)
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Part 2 text-mining SVG figures.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--figure-dir", type=Path, default=DEFAULT_FIGURE_DIR)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = write_figures(args.output_dir, args.figure_dir)
    print(json.dumps({"figures": [str(path) for path in paths]}, indent=2))


if __name__ == "__main__":
    main()
