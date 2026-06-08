"""Construct the Part 3 Organizational Authenticity Index.

This module is the scoring spine for Part 3. It reads the finalized Part 1 and Part 2
company-year panels, converts their shared ``theme_evidence`` payloads into aligned 12-theme
vectors, computes the primary keyword-taxonomy overlap score, and appends supplementary
robustness/context fields. It deliberately keeps every target company-year and uses status fields
to explain why a row is or is not scoreable.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from org_auth_part3.constants import (
    INDEX_OUTPUT,
    OUTPUT_DIR,
    PART1_DATASET,
    PART2_DATASET,
    SEMANTIC_EMBEDDING_MODEL,
    SEMANTIC_OUTPUT,
    TAXONOMY_VERSION,
    THEME_IDS,
    THEME_LABELS,
)
from org_auth_part3.semantic import write_semantic_similarity


def parse_theme_vector(value: Any, theme_ids: Sequence[str] = THEME_IDS) -> dict[str, int]:
    """Parse a JSON theme-evidence payload into an ordered theme-count vector.

    The upstream Part 1 and Part 2 files store theme evidence as a JSON list of objects. The score
    only needs the deterministic ``match_count`` values, so malformed, missing, or unknown-theme
    entries are treated as zero signal rather than crashing the full 450-row panel build.
    """

    counts = {theme_id: 0 for theme_id in theme_ids}
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return counts
    if not isinstance(value, str) or not value.strip():
        return counts
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return counts
    if not isinstance(payload, list):
        return counts
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        theme_id = item.get("theme_id")
        if theme_id not in counts:
            continue
        try:
            counts[theme_id] += int(item.get("match_count") or 0)
        except (TypeError, ValueError):
            continue
    return counts


def normalize_vector(counts: Mapping[str, int]) -> dict[str, float]:
    """Convert nonnegative theme counts to shares while preserving zero vectors."""

    total = sum(max(int(value), 0) for value in counts.values())
    if total <= 0:
        return {key: 0.0 for key in counts}
    return {key: max(int(value), 0) / total for key, value in counts.items()}


def overlap_alignment(stated: Mapping[str, float], disclosure: Mapping[str, float]) -> float:
    """Return the percentage of stated-values emphasis mirrored in disclosure emphasis."""

    return round(100 * sum(min(stated[key], disclosure[key]) for key in THEME_IDS), 6)


def cosine_alignment(stated: Mapping[str, float], disclosure: Mapping[str, float]) -> float:
    """Return cosine similarity on theme-share vectors as a 0-100 score."""

    dot = sum(stated[key] * disclosure[key] for key in THEME_IDS)
    stated_norm = math.sqrt(sum(stated[key] ** 2 for key in THEME_IDS))
    disclosure_norm = math.sqrt(sum(disclosure[key] ** 2 for key in THEME_IDS))
    if stated_norm == 0 or disclosure_norm == 0:
        return 0.0
    return round(100 * dot / (stated_norm * disclosure_norm), 6)


def l1_alignment(stated: Mapping[str, float], disclosure: Mapping[str, float]) -> float:
    """Return normalized L1 overlap on theme-share vectors as a 0-100 score."""

    distance = sum(abs(stated[key] - disclosure[key]) for key in THEME_IDS)
    return round(100 * (1 - 0.5 * distance), 6)


def jaccard_theme_overlap(stated: Mapping[str, int], disclosure: Mapping[str, int]) -> float:
    """Return binary theme-set Jaccard overlap as a 0-100 score."""

    stated_set = {key for key, value in stated.items() if value > 0}
    disclosure_set = {key for key, value in disclosure.items() if value > 0}
    union = stated_set | disclosure_set
    if not union:
        return 0.0
    return round(100 * len(stated_set & disclosure_set) / len(union), 6)


def score_status(
    part1_status: str, part2_status: str, stated_total: int, disclosure_total: int
) -> tuple[str, str]:
    """Classify whether an authenticity score can be computed for one company-year."""

    part1_missing = part1_status != "usable"
    part2_missing = part2_status != "collected"
    if part1_missing and part2_missing:
        return "missing_both", "Part 1 is not usable and Part 2 is not collected."
    if part1_missing:
        return "missing_part1", "Part 1 stated-values observation is not usable."
    if part2_missing:
        return "missing_part2", "Part 2 proxy disclosure is not collected."
    if stated_total <= 0:
        return (
            "insufficient_stated_theme_signal",
            "Part 1 is usable but has no deterministic theme matches.",
        )
    if disclosure_total <= 0:
        return (
            "insufficient_disclosure_theme_signal",
            "Part 2 is collected but has no deterministic theme matches.",
        )
    return "scored", ""


def top_themes(counts: Mapping[str, int], *, limit: int = 3) -> str:
    """Serialize the leading themes by raw match count."""

    rows = [
        {
            "theme_id": theme_id,
            "theme_label": THEME_LABELS[theme_id],
            "match_count": int(count),
        }
        for theme_id, count in counts.items()
        if int(count) > 0
    ]
    rows.sort(key=lambda row: (-row["match_count"], row["theme_id"]))
    return json.dumps(rows[:limit], ensure_ascii=True)


def theme_gap_summary(stated: Mapping[str, float], disclosure: Mapping[str, float]) -> str:
    """Serialize the largest stated-minus-disclosure theme-share gaps."""

    rows = [
        {
            "theme_id": theme_id,
            "theme_label": THEME_LABELS[theme_id],
            "stated_share": round(stated[theme_id], 6),
            "disclosure_share": round(disclosure[theme_id], 6),
            "stated_minus_disclosure": round(stated[theme_id] - disclosure[theme_id], 6),
        }
        for theme_id in THEME_IDS
    ]
    rows.sort(key=lambda row: (-abs(row["stated_minus_disclosure"]), row["theme_id"]))
    return json.dumps(rows[:5], ensure_ascii=True)


def _parse_linguistic_metric(value: Any, key: str) -> float | None:
    """Extract a numeric Part 2 linguistic metric from its JSON payload."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    raw = payload.get(key)
    try:
        return round(float(raw), 6)
    except (TypeError, ValueError):
        return None


def _load_semantic_frame(semantic_path: Path = SEMANTIC_OUTPUT) -> pd.DataFrame:
    """Load optional semantic similarity output, preserving schema when absent."""

    columns = [
        "ticker",
        "year",
        "semantic_text_similarity",
        "semantic_similarity_status",
        "semantic_similarity_gap_reason",
        "semantic_embedding_model",
    ]
    if not semantic_path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(semantic_path)


def build_index(
    part1_path: Path = PART1_DATASET,
    part2_path: Path = PART2_DATASET,
    semantic_path: Path = SEMANTIC_OUTPUT,
) -> pd.DataFrame:
    """Build the 450-row Part 3 authenticity panel."""

    # The merge is intentionally inner on the required target keys: Part 1 and Part 2 both carry
    # the complete 50-company by 9-year grid, so anything other than 450 rows signals an upstream
    # contract break rather than ordinary missingness.
    part1 = pd.read_csv(part1_path)
    part2 = pd.read_csv(part2_path)
    merged = part1.merge(part2, on=["ticker", "year"], suffixes=("_part1", "_part2"))
    if len(merged) != 450:
        raise ValueError(f"Expected 450 merged company-years, found {len(merged)}")

    records: list[dict[str, Any]] = []
    for row in merged.to_dict("records"):
        stated_counts = parse_theme_vector(row.get("theme_evidence_part1"))
        disclosure_counts = parse_theme_vector(row.get("theme_evidence_part2"))
        stated_total = sum(stated_counts.values())
        disclosure_total = sum(disclosure_counts.values())
        stated_share = normalize_vector(stated_counts)
        disclosure_share = normalize_vector(disclosure_counts)
        status, gap_reason = score_status(
            str(row.get("observation_status") or ""),
            str(row.get("collection_status") or ""),
            stated_total,
            disclosure_total,
        )
        scored = status == "scored"
        # Non-scoreable rows retain diagnostics and provenance, but score-like fields stay null so
        # missing text or missing theme evidence is never interpreted as zero alignment.
        record = {
            "ticker": row["ticker"],
            "company_name": row.get("company_name_part1") or row.get("company_name_part2"),
            "sector": row.get("sector_part1") or row.get("sector_part2"),
            "year": int(row["year"]),
            "part1_observation_status": row.get("observation_status"),
            "part1_gap_reason": row.get("gap_reason_part1"),
            "part2_collection_status": row.get("collection_status"),
            "part2_gap_reason": row.get("gap_reason_part2"),
            "score_status": status,
            "score_gap_reason": gap_reason,
            "authenticity_index": overlap_alignment(stated_share, disclosure_share)
            if scored
            else None,
            "cosine_alignment": cosine_alignment(stated_share, disclosure_share)
            if scored
            else None,
            "l1_alignment": l1_alignment(stated_share, disclosure_share) if scored else None,
            "jaccard_theme_overlap": jaccard_theme_overlap(stated_counts, disclosure_counts)
            if scored
            else None,
            "stated_theme_total_matches": stated_total,
            "disclosure_theme_total_matches": disclosure_total,
            "stated_top_themes": top_themes(stated_counts),
            "disclosure_top_themes": top_themes(disclosure_counts),
            "theme_gap_summary": theme_gap_summary(stated_share, disclosure_share),
            "part1_clean_text_sha256": row.get("clean_text_sha256_part1"),
            "part2_clean_text_sha256": row.get("clean_text_sha256_part2"),
            "part1_source_url": row.get("source_url_part1"),
            "part2_sec_archive_url": row.get("sec_archive_url"),
            "taxonomy_version": TAXONOMY_VERSION,
            "part2_action_evidence_rate": _parse_linguistic_metric(
                row.get("linguistic_metrics_part2"),
                "action_or_evidence_rate_per_100_words",
            ),
            "part2_stakeholder_rate": _parse_linguistic_metric(
                row.get("linguistic_metrics_part2"),
                "stakeholder_rate_per_100_words",
            ),
            "part2_word_count": row.get("word_count"),
        }
        records.append(record)
    frame = pd.DataFrame(records).sort_values(["ticker", "year"]).reset_index(drop=True)
    # Semantic similarity is a supplementary robustness layer. It is merged after the deterministic
    # score construction so the primary index can still be built and validated if embeddings are
    # unavailable in a constrained environment.
    semantic = _load_semantic_frame(semantic_path)
    if not semantic.empty:
        frame = frame.merge(semantic, on=["ticker", "year"], how="left")
    else:
        frame["semantic_text_similarity"] = None
        frame["semantic_similarity_status"] = "not_computed"
        frame["semantic_similarity_gap_reason"] = (
            "Semantic similarity output was not generated for this index run."
        )
        frame["semantic_embedding_model"] = ""
    computed_semantic = frame["semantic_similarity_status"] == "computed"
    frame.loc[computed_semantic, "semantic_embedding_model"] = frame.loc[
        computed_semantic, "semantic_embedding_model"
    ].fillna(SEMANTIC_EMBEDDING_MODEL)
    frame.loc[~computed_semantic, "semantic_embedding_model"] = frame.loc[
        ~computed_semantic, "semantic_embedding_model"
    ].fillna("")
    frame["sector_percentile"] = None
    frame["sector_z_score"] = None
    scored_mask = frame["score_status"] == "scored"
    # Sector-adjusted context is computed only within observed scored rows. We do not impute sector
    # means for non-scored company-years because missingness is part of the audit trail.
    for _, sector_index in frame[scored_mask].groupby("sector").groups.items():
        scores = frame.loc[sector_index, "authenticity_index"]
        frame.loc[sector_index, "sector_percentile"] = scores.rank(pct=True).round(6)
        std = scores.std()
        if std and not math.isnan(std):
            frame.loc[sector_index, "sector_z_score"] = ((scores - scores.mean()) / std).round(6)
        else:
            frame.loc[sector_index, "sector_z_score"] = 0.0
    return frame


def write_index(
    output_path: Path = INDEX_OUTPUT,
    part1_path: Path = PART1_DATASET,
    part2_path: Path = PART2_DATASET,
    semantic_path: Path = SEMANTIC_OUTPUT,
) -> pd.DataFrame:
    """Write the final Part 3 index panel and return it."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Refresh semantic output first so the final panel always contains the latest semantic status
    # and similarity fields when the index command is run end to end.
    write_semantic_similarity(semantic_path, part1_path, part2_path)
    df = build_index(part1_path, part2_path, semantic_path)
    df.to_csv(output_path, index=False)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part1", type=Path, default=PART1_DATASET)
    parser.add_argument("--part2", type=Path, default=PART2_DATASET)
    parser.add_argument("--semantic", type=Path, default=SEMANTIC_OUTPUT)
    parser.add_argument("--output", type=Path, default=INDEX_OUTPUT)
    args = parser.parse_args()
    df = write_index(args.output, args.part1, args.part2, args.semantic)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": len(df),
                "score_status_counts": df["score_status"].value_counts().sort_index().to_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
