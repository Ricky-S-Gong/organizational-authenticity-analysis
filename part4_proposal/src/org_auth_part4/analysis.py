"""Build Part 4 proxy-genre sensitivity diagnostics.

This module tests whether the Part 3 authenticity index is sensitive to the genre of the
underlying ``DEF 14A`` proxy statements. It is deliberately deterministic: phrase dictionaries
define proxy-genre pressure, every company-year is retained, and non-diagnostic rows receive
explicit statuses rather than being dropped.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from org_auth_part4.constants import (
    CASE_AUDIT_OUTPUT,
    CORRELATION_OUTPUT,
    DIAGNOSTICS_OUTPUT,
    GENRE_DICTIONARIES,
    OUTPUT_DIR,
    PART2_COMPACT,
    PART2_FULL,
    PART3_INDEX,
    QUADRANT_OUTPUT,
    REGRESSION_OUTPUT,
    SUMMARY_OUTPUT,
)


def normalize_text(text: str | float | None) -> str:
    """Lowercase and compact text for deterministic phrase matching."""

    if text is None or (isinstance(text, float) and math.isnan(text)):
        return ""
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def count_phrase_matches(text: str, phrases: Sequence[str]) -> int:
    """Count case-insensitive phrase occurrences with token boundaries."""

    normalized = normalize_text(text)
    if not normalized:
        return 0
    total = 0
    for phrase in phrases:
        # Token boundaries avoid counting governance terms inside unrelated longer words while
        # still allowing multiword phrases such as "annual meeting" or "proxy card".
        pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
        total += len(re.findall(pattern, normalized))
    return total


def rate_per_1000_words(count: int | float | None, word_count: int | float | None) -> float:
    """Return a normalized rate while preserving zero-word rows as zero signal."""

    try:
        count_value = float(count or 0)
        words = float(word_count or 0)
    except (TypeError, ValueError):
        return 0.0
    if words <= 0:
        return 0.0
    return round(1000 * count_value / words, 6)


def zscore(values: pd.Series) -> pd.Series:
    """Return sample z-scores, keeping missing values missing."""

    numeric = pd.to_numeric(values, errors="coerce")
    mean = numeric.mean()
    std = numeric.std(ddof=0)
    if pd.isna(std) or std == 0:
        return numeric * 0
    return (numeric - mean) / std


def composite_genre_pressure(frame: pd.DataFrame) -> pd.Series:
    """Average available z-scored genre rates for rows with proxy text."""

    rate_columns = [
        "shareholder_mechanics_rate",
        "governance_boilerplate_rate",
        "legal_procedural_rate",
    ]
    z_frame = pd.DataFrame(index=frame.index)
    collected = frame["genre_status"] == "computed"
    for column in rate_columns:
        # Z-scores are estimated only among rows with usable proxy text so missing proxy rows do
        # not compress the distribution toward zero.
        z_frame[column.replace("_rate", "_z")] = zscore(frame.loc[collected, column])
    return z_frame.mean(axis=1, skipna=True)


def read_text_from_path(path_value: Any) -> str:
    """Read a local proxy text artifact if it exists."""

    if path_value is None or (isinstance(path_value, float) and math.isnan(path_value)):
        return ""
    path = Path(str(path_value))
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def load_part2_with_text(
    compact_path: Path = PART2_COMPACT,
    full_path: Path = PART2_FULL,
) -> pd.DataFrame:
    """Load Part 2 rows and attach clean proxy text when available."""

    compact = pd.read_csv(compact_path)
    if full_path.exists():
        full = pd.read_csv(full_path, usecols=["ticker", "year", "page_text_clean"])
        compact = compact.merge(full, on=["ticker", "year"], how="left")
    else:
        compact["page_text_clean"] = ""
    missing_text = compact["page_text_clean"].fillna("").astype(str).str.len() == 0
    if missing_text.any():
        # The compact Part 2 panel stores text paths when full text is not committed. Reading those
        # paths preserves the same code path for local reproduction without requiring new downloads.
        compact.loc[missing_text, "page_text_clean"] = compact.loc[missing_text, "text_path"].map(
            read_text_from_path
        )
    return compact


def semantic_0_100(value: Any) -> float | None:
    """Convert Part 3 semantic similarity from -100..100-ish to a 0-100 comparison scale."""

    try:
        return round((float(value) + 100) / 2, 6)
    except (TypeError, ValueError):
        return None


def assign_terciles(values: pd.Series) -> pd.Series:
    """Assign low/medium/high terciles to available proxy-genre pressure values."""

    labels = pd.Series(pd.NA, index=values.index, dtype="object")
    available = values.dropna()
    if available.empty:
        return labels
    ranked = available.rank(method="first")
    terciles = pd.qcut(ranked, q=3, labels=["low", "medium", "high"])
    labels.loc[available.index] = terciles.astype(str)
    return labels


def keyword_semantic_quadrants(frame: pd.DataFrame) -> pd.Series:
    """Classify scored rows by keyword index and rescaled semantic similarity medians."""

    labels = pd.Series(pd.NA, index=frame.index, dtype="object")
    scored = frame[
        frame["authenticity_index"].notna() & frame["semantic_0_100"].notna()
    ].copy()
    if scored.empty:
        return labels
    keyword_median = scored["authenticity_index"].median()
    semantic_median = scored["semantic_0_100"].median()
    for idx, row in scored.iterrows():
        keyword_high = row["authenticity_index"] >= keyword_median
        semantic_high = row["semantic_0_100"] >= semantic_median
        if keyword_high and semantic_high:
            labels.loc[idx] = "both_high"
        elif not keyword_high and not semantic_high:
            labels.loc[idx] = "both_low"
        elif keyword_high:
            labels.loc[idx] = "keyword_high_only"
        else:
            labels.loc[idx] = "semantic_high_only"
    return labels


def build_diagnostics(
    part3_path: Path = PART3_INDEX,
    part2_compact_path: Path = PART2_COMPACT,
    part2_full_path: Path = PART2_FULL,
) -> pd.DataFrame:
    """Build the 450-row Part 4 diagnostic panel."""

    part3 = pd.read_csv(part3_path)
    part2 = load_part2_with_text(part2_compact_path, part2_full_path)
    merged = part3.merge(
        part2[
            [
                "ticker",
                "year",
                "collection_status",
                "gap_reason",
                "word_count",
                "text_path",
                "page_text_clean",
            ]
        ],
        on=["ticker", "year"],
        how="left",
        suffixes=("", "_part2"),
    )
    if len(merged) != 450:
        raise ValueError(f"Expected 450 company-years, found {len(merged)}")

    records: list[dict[str, Any]] = []
    for row in merged.to_dict("records"):
        text = row.get("page_text_clean") or ""
        collection_status = row.get("collection_status")
        has_text = bool(normalize_text(text))
        # Keep every target company-year and encode why genre diagnostics are unavailable instead
        # of filtering out uncollected proxies or collected rows whose clean text is missing.
        if collection_status != "collected":
            genre_status = "missing_proxy"
            genre_gap_reason = row.get("gap_reason") or "Part 2 proxy disclosure is not collected."
        elif not has_text:
            genre_status = "missing_proxy_text"
            genre_gap_reason = "Part 2 proxy disclosure is collected but clean text is unavailable."
        else:
            genre_status = "computed"
            genre_gap_reason = ""
        word_count = row.get("part2_word_count")
        if pd.isna(word_count):
            word_count = row.get("word_count")
        record = {
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "sector": row["sector"],
            "year": int(row["year"]),
            "score_status": row.get("score_status"),
            "genre_status": genre_status,
            "genre_gap_reason": genre_gap_reason,
            "part2_collection_status": row.get("part2_collection_status"),
            "authenticity_index": row.get("authenticity_index"),
            "semantic_text_similarity": row.get("semantic_text_similarity"),
            "semantic_0_100": semantic_0_100(row.get("semantic_text_similarity")),
            "part2_word_count": word_count,
        }
        record["keyword_minus_semantic"] = (
            round(float(record["authenticity_index"]) - float(record["semantic_0_100"]), 6)
            if pd.notna(record["authenticity_index"]) and record["semantic_0_100"] is not None
            else None
        )
        for family, phrases in GENRE_DICTIONARIES.items():
            count = count_phrase_matches(text, phrases) if genre_status == "computed" else 0
            record[f"{family}_count"] = count
            record[f"{family}_rate"] = rate_per_1000_words(count, word_count)
        records.append(record)

    diagnostics = pd.DataFrame(records)
    diagnostics["proxy_genre_pressure"] = composite_genre_pressure(diagnostics).round(6)
    diagnostics.loc[diagnostics["genre_status"] != "computed", "proxy_genre_pressure"] = np.nan
    diagnostics["genre_pressure_tercile"] = assign_terciles(diagnostics["proxy_genre_pressure"])
    diagnostics["keyword_semantic_quadrant"] = keyword_semantic_quadrants(diagnostics)
    return diagnostics


def distribution_row(frame: pd.DataFrame) -> dict[str, Any]:
    """Return overall distribution fields for proxy-genre pressure."""

    values = frame["proxy_genre_pressure"].dropna()
    return {
        "group": "overall",
        "company_years": len(frame),
        "diagnostic_company_years": len(values),
        "scored_company_years": int(frame["authenticity_index"].notna().sum()),
        "mean_proxy_genre_pressure": round(values.mean(), 6),
        "median_proxy_genre_pressure": round(values.median(), 6),
        "mean_authenticity_index": round(frame["authenticity_index"].mean(), 6),
        "median_authenticity_index": round(frame["authenticity_index"].median(), 6),
    }


def genre_pressure_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize proxy-genre pressure overall and by tercile."""

    rows = [distribution_row(frame)]
    for tercile, group in frame.dropna(subset=["genre_pressure_tercile"]).groupby(
        "genre_pressure_tercile", sort=True
    ):
        rows.append(
            {
                "group": f"tercile_{tercile}",
                "company_years": len(group),
                "diagnostic_company_years": int(group["proxy_genre_pressure"].notna().sum()),
                "scored_company_years": int(group["authenticity_index"].notna().sum()),
                "mean_proxy_genre_pressure": round(group["proxy_genre_pressure"].mean(), 6),
                "median_proxy_genre_pressure": round(group["proxy_genre_pressure"].median(), 6),
                "mean_authenticity_index": round(group["authenticity_index"].mean(), 6),
                "median_authenticity_index": round(group["authenticity_index"].median(), 6),
            }
        )
    return pd.DataFrame(rows)


def correlation_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Correlate genre pressure with Part 3 diagnostics."""

    rows = []
    for metric in ["authenticity_index", "semantic_0_100", "keyword_minus_semantic"]:
        subset = frame[["proxy_genre_pressure", metric]].dropna()
        rows.append(
            {
                "comparison_metric": metric,
                "company_years": len(subset),
                "pearson_correlation": round(
                    subset["proxy_genre_pressure"].corr(subset[metric], method="pearson"), 6
                )
                if len(subset) > 1
                else None,
                "spearman_correlation": round(
                    subset["proxy_genre_pressure"].corr(subset[metric], method="spearman"), 6
                )
                if len(subset) > 1
                else None,
            }
        )
    return pd.DataFrame(rows)


def quadrant_genre_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize genre pressure by keyword-semantic quadrant."""

    rows = []
    grouped = frame.dropna(subset=["keyword_semantic_quadrant"]).groupby(
        "keyword_semantic_quadrant", sort=True
    )
    for quadrant, group in grouped:
        rows.append(
            {
                "quadrant": quadrant,
                "company_years": len(group),
                "mean_proxy_genre_pressure": round(group["proxy_genre_pressure"].mean(), 6),
                "mean_authenticity_index": round(group["authenticity_index"].mean(), 6),
                "mean_semantic_0_100": round(group["semantic_0_100"].mean(), 6),
                "mean_keyword_minus_semantic": round(group["keyword_minus_semantic"].mean(), 6),
            }
        )
    return pd.DataFrame(rows)


def _case_record(row: pd.Series, bucket: str) -> dict[str, Any]:
    """Serialize a row for qualitative audit."""

    return {
        "audit_bucket": bucket,
        "ticker": row["ticker"],
        "company_name": row["company_name"],
        "sector": row["sector"],
        "year": int(row["year"]),
        "authenticity_index": round(float(row["authenticity_index"]), 6),
        "semantic_0_100": round(float(row["semantic_0_100"]), 6),
        "keyword_minus_semantic": round(float(row["keyword_minus_semantic"]), 6),
        "proxy_genre_pressure": round(float(row["proxy_genre_pressure"]), 6),
        "genre_pressure_tercile": row["genre_pressure_tercile"],
        "keyword_semantic_quadrant": row["keyword_semantic_quadrant"],
    }


def case_audit_targets(frame: pd.DataFrame, *, per_bucket: int = 5) -> pd.DataFrame:
    """Select OAI-by-SS diagnostic cases for manual review.

    The case type is intentionally based only on the two primary alignment diagnostics:
    Organizational Authenticity Index (OAI) and whole-text semantic similarity (SS). Proxy genre
    pressure remains in the output as context, but it does not define the case bucket.
    """

    scored = frame.dropna(
        subset=[
            "authenticity_index",
            "semantic_0_100",
            "keyword_minus_semantic",
            "proxy_genre_pressure",
        ]
    ).copy()
    if scored.empty:
        return pd.DataFrame()
    low_cut = scored["authenticity_index"].quantile(0.25)
    high_cut = scored["authenticity_index"].quantile(0.75)
    low_semantic_cut = scored["semantic_0_100"].quantile(0.25)
    high_semantic_cut = scored["semantic_0_100"].quantile(0.75)

    buckets: list[tuple[str, pd.DataFrame, str]] = [
        (
            "low_oai_low_ss",
            scored[
                (scored["authenticity_index"] <= low_cut)
                & (scored["semantic_0_100"] <= low_semantic_cut)
            ].sort_values(["authenticity_index", "semantic_0_100"], ascending=[True, True]),
            "Low alignment on both OAI and whole-text semantic similarity.",
        ),
        (
            "low_oai_high_ss",
            scored[
                (scored["authenticity_index"] <= low_cut)
                & (scored["semantic_0_100"] >= high_semantic_cut)
            ].sort_values(["semantic_0_100", "authenticity_index"], ascending=[False, True]),
            "Broad semantic similarity but weak theme-distribution alignment.",
        ),
        (
            "high_oai_low_ss",
            scored[
                (scored["authenticity_index"] >= high_cut)
                & (scored["semantic_0_100"] <= low_semantic_cut)
            ].sort_values(["authenticity_index", "semantic_0_100"], ascending=[False, True]),
            "Strong theme-distribution alignment with weaker whole-text semantic similarity.",
        ),
        (
            "high_oai_high_ss",
            scored[
                (scored["authenticity_index"] >= high_cut)
                & (scored["semantic_0_100"] >= high_semantic_cut)
            ].sort_values(["authenticity_index", "semantic_0_100"], ascending=[False, False]),
            "Robust alignment across both OAI and whole-text semantic similarity.",
        ),
    ]
    rows = []
    for bucket, group, interpretation in buckets:
        for _, row in group.head(per_bucket).iterrows():
            record = _case_record(row, bucket)
            record["interpretation_prompt"] = interpretation
            rows.append(record)
    return pd.DataFrame(rows)


def regression_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Run a descriptive OLS-style regression with year and sector fixed effects."""

    data = frame[
        ["authenticity_index", "proxy_genre_pressure", "part2_word_count", "year", "sector"]
    ].dropna()
    if len(data) < 10:
        return pd.DataFrame()
    design = pd.DataFrame(
        {
            "intercept": 1.0,
            "proxy_genre_pressure": data["proxy_genre_pressure"].astype(float),
            "log_part2_word_count": np.log1p(data["part2_word_count"].astype(float)),
        },
        index=data.index,
    )
    design = pd.concat(
        [
            design,
            pd.get_dummies(data["sector"], prefix="sector", drop_first=True, dtype=float),
            pd.get_dummies(data["year"].astype(int), prefix="year", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    y = data["authenticity_index"].astype(float).to_numpy()
    x = design.to_numpy(dtype=float)
    # The assignment asks for exploratory diagnostics, so this deliberately reports a transparent
    # least-squares description rather than treating the coefficient as a causal estimate.
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    ss_total = float(((y - y.mean()) ** 2).sum())
    ss_resid = float(((y - fitted) ** 2).sum())
    r_squared = 1 - ss_resid / ss_total if ss_total else np.nan
    return pd.DataFrame(
        [
            {
                "term": column,
                "coefficient": round(float(value), 6),
                "company_years": len(data),
                "r_squared": round(float(r_squared), 6),
                "model": (
                    "authenticity_index ~ proxy_genre_pressure + log(word_count) "
                    "+ sector FE + year FE"
                ),
            }
            for column, value in zip(design.columns, beta, strict=True)
        ]
    )


def write_analysis_outputs() -> dict[str, str]:
    """Write all Part 4 analysis outputs."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    diagnostics = build_diagnostics()
    outputs: Mapping[Path, pd.DataFrame] = {
        DIAGNOSTICS_OUTPUT: diagnostics,
        SUMMARY_OUTPUT: genre_pressure_summary(diagnostics),
        CORRELATION_OUTPUT: correlation_summary(diagnostics),
        QUADRANT_OUTPUT: quadrant_genre_summary(diagnostics),
        CASE_AUDIT_OUTPUT: case_audit_targets(diagnostics),
        REGRESSION_OUTPUT: regression_summary(diagnostics),
    }
    for path, frame in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    return {str(path): str(len(frame)) for path, frame in outputs.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(write_analysis_outputs(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
