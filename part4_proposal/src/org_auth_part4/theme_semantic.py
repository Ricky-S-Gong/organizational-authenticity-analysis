"""Theme-level semantic comparison for Part 4.

This module compares Part 1 and Part 2 evidence excerpts within the same taxonomy theme. Unlike
the Part 3 whole-text semantic check, it asks whether a theme that appears in both sources is used
in similar local contexts.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from org_auth_part4.constants import (
    PART2_COMPACT,
    PART3_INDEX,
    THEME_DICTIONARIES,
    THEME_SEMANTIC_OUTPUT,
    THEME_SEMANTIC_SUMMARY_OUTPUT,
)

PART1_DATASET = Path("part1_stated_values/outputs/part1_company_year.csv")


def parse_theme_evidence(value: Any) -> dict[str, dict[str, Any]]:
    """Parse upstream JSON theme evidence into a theme-indexed mapping."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, list):
        return {}
    parsed = {}
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        theme_id = item.get("theme_id")
        if not theme_id:
            continue
        # Upstream evidence is stored as a list of theme records. Re-indexing by theme_id makes the
        # Part 1 and Part 2 evidence directly comparable for the same taxonomy category.
        parsed[str(theme_id)] = {
            "match_count": int(item.get("match_count") or 0),
            "evidence_excerpts": [
                str(excerpt)
                for excerpt in item.get("evidence_excerpts", [])
                if str(excerpt).strip()
            ],
        }
    return parsed


def compact_excerpts(excerpts: list[str], *, max_excerpts: int = 8, max_chars: int = 4500) -> str:
    """Create a bounded representative text from theme-level evidence excerpts."""

    # Bound excerpt volume so firms with many repeated proxy matches do not dominate semantic
    # comparison simply because they supply more local evidence text.
    text = " ".join(" ".join(excerpt.split()) for excerpt in excerpts[:max_excerpts])
    return text[:max_chars]


def _tfidf_similarity(left: str, right: str) -> float | None:
    """Return TF-IDF cosine similarity scaled 0-100 for fallback semantic comparison."""

    if not left or not right:
        return None
    matrix = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform([left, right])
    return round(float(cosine_similarity(matrix[0], matrix[1])[0][0] * 100), 6)


def _embedding_similarities(pairs: list[tuple[str, str]], model_name: str) -> list[float] | None:
    """Compute sentence-transformer cosine similarities, returning None when unavailable."""

    if not pairs:
        return []
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        # Returning None triggers the deterministic TF-IDF fallback, which keeps the pipeline
        # reproducible on machines without the embedding package or cached model weights.
        return None
    try:
        model = SentenceTransformer(model_name)
        texts = [text for pair in pairs for text in pair]
        embeddings = model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception:
        return None
    similarities = []
    for idx in range(0, len(embeddings), 2):
        similarities.append(round(float(np.dot(embeddings[idx], embeddings[idx + 1]) * 100), 6))
    return similarities


def _share(match_count: int, total: int) -> float:
    """Return a zero-safe theme share."""

    return round(match_count / total, 6) if total else 0.0


def build_theme_pair_frame(
    part1_path: Path = PART1_DATASET,
    part2_path: Path = PART2_COMPACT,
    part3_path: Path = PART3_INDEX,
) -> pd.DataFrame:
    """Build a 12-theme-by-company-year evidence comparison frame."""

    part1 = pd.read_csv(part1_path)[["ticker", "year", "theme_evidence"]].rename(
        columns={"theme_evidence": "theme_evidence_part1"}
    )
    part2 = pd.read_csv(part2_path)[["ticker", "year", "theme_evidence"]].rename(
        columns={"theme_evidence": "theme_evidence_part2"}
    )
    part3 = pd.read_csv(part3_path)[
        ["ticker", "year", "score_status", "authenticity_index", "semantic_text_similarity"]
    ]
    merged = part3.merge(part1, on=["ticker", "year"], how="left").merge(
        part2, on=["ticker", "year"], how="left"
    )
    rows = []
    for row in merged.to_dict("records"):
        stated = parse_theme_evidence(row.get("theme_evidence_part1"))
        disclosure = parse_theme_evidence(row.get("theme_evidence_part2"))
        stated_total = sum(item["match_count"] for item in stated.values())
        disclosure_total = sum(item["match_count"] for item in disclosure.values())
        for theme_id in THEME_DICTIONARIES:
            # Emit all 12 themes for every company-year, including missing evidence statuses. This
            # makes absence of theme evidence visible instead of narrowing the output to successes.
            stated_item = stated.get(theme_id, {"match_count": 0, "evidence_excerpts": []})
            disclosure_item = disclosure.get(theme_id, {"match_count": 0, "evidence_excerpts": []})
            stated_text = compact_excerpts(stated_item["evidence_excerpts"])
            disclosure_text = compact_excerpts(disclosure_item["evidence_excerpts"])
            if not stated_text and not disclosure_text:
                status = "missing_both_theme_evidence"
            elif not stated_text:
                status = "missing_stated_theme_evidence"
            elif not disclosure_text:
                status = "missing_disclosure_theme_evidence"
            else:
                status = "pending"
            rows.append(
                {
                    "ticker": row["ticker"],
                    "year": int(row["year"]),
                    "theme_id": theme_id,
                    "score_status": row["score_status"],
                    "authenticity_index": row["authenticity_index"],
                    "whole_text_semantic_similarity": row["semantic_text_similarity"],
                    "theme_semantic_status": status,
                    "theme_semantic_similarity": None,
                    "theme_semantic_method": "",
                    "stated_excerpt_count": len(stated_item["evidence_excerpts"]),
                    "disclosure_excerpt_count": len(disclosure_item["evidence_excerpts"]),
                    "stated_theme_match_count": stated_item["match_count"],
                    "disclosure_theme_match_count": disclosure_item["match_count"],
                    "stated_theme_share": _share(stated_item["match_count"], stated_total),
                    "disclosure_theme_share": _share(
                        disclosure_item["match_count"], disclosure_total
                    ),
                    "stated_theme_excerpt_text": stated_text,
                    "disclosure_theme_excerpt_text": disclosure_text,
                }
            )
    return pd.DataFrame(rows)


def compute_theme_semantic_scores(
    frame: pd.DataFrame,
    *,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> pd.DataFrame:
    """Compute theme-level semantic similarities for rows with evidence on both sides."""

    output = frame.copy()
    eligible = output["theme_semantic_status"] == "pending"
    pairs = list(
        zip(
            output.loc[eligible, "stated_theme_excerpt_text"],
            output.loc[eligible, "disclosure_theme_excerpt_text"],
            strict=True,
        )
    )
    embedding_scores = _embedding_similarities(pairs, model_name)
    if embedding_scores is not None:
        output.loc[eligible, "theme_semantic_similarity"] = embedding_scores
        output.loc[eligible, "theme_semantic_status"] = "computed"
        output.loc[eligible, "theme_semantic_method"] = model_name
    else:
        # The fallback has a different interpretation from transformer embeddings, so the method is
        # written to each row and can be audited downstream.
        fallback_scores = [_tfidf_similarity(left, right) for left, right in pairs]
        output.loc[eligible, "theme_semantic_similarity"] = fallback_scores
        output.loc[eligible, "theme_semantic_status"] = "computed_tfidf_fallback"
        output.loc[eligible, "theme_semantic_method"] = "tfidf_unigram_bigram_cosine"
    output["theme_share_gap_abs"] = (
        output["stated_theme_share"] - output["disclosure_theme_share"]
    ).abs()
    return output


def build_theme_semantic_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize theme-level semantic comparison by theme."""

    computed = frame[frame["theme_semantic_similarity"].notna()].copy()
    rows = []
    for theme_id, group in computed.groupby("theme_id", sort=True):
        rows.append(
            {
                "theme_id": theme_id,
                "computed_company_years": len(group),
                "mean_theme_semantic_similarity": round(
                    group["theme_semantic_similarity"].mean(), 6
                ),
                "median_theme_semantic_similarity": round(
                    group["theme_semantic_similarity"].median(), 6
                ),
                "mean_theme_share_gap_abs": round(group["theme_share_gap_abs"].mean(), 6),
                "mean_authenticity_index": round(group["authenticity_index"].mean(), 6),
            }
        )
    return pd.DataFrame(rows).sort_values("mean_theme_semantic_similarity", ascending=False)


def write_theme_semantic_outputs() -> dict[str, str]:
    """Write theme-level semantic outputs."""

    frame = compute_theme_semantic_scores(build_theme_pair_frame())
    summary = build_theme_semantic_summary(frame)
    THEME_SEMANTIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.drop(columns=["stated_theme_excerpt_text", "disclosure_theme_excerpt_text"]).to_csv(
        THEME_SEMANTIC_OUTPUT, index=False
    )
    summary.to_csv(THEME_SEMANTIC_SUMMARY_OUTPUT, index=False)
    return {
        str(THEME_SEMANTIC_OUTPUT): str(len(frame)),
        str(THEME_SEMANTIC_SUMMARY_OUTPUT): str(len(summary)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(write_theme_semantic_outputs(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
