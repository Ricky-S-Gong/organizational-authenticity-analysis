"""Semantic similarity robustness checks for the Part 3 index.

The primary Part 3 score is keyword-taxonomy based. This module adds a separate whole-text
embedding comparison so the analysis can ask whether two documents are semantically close even
when the deterministic theme distribution is weak. The output is intentionally kept separate from
the primary score and then merged into the final panel as a robustness diagnostic.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from org_auth_part3.constants import (
    PART1_DATASET,
    PART2_DATASET,
    SEMANTIC_EMBEDDING_MODEL,
    SEMANTIC_OUTPUT,
    SEMANTIC_REPRESENTATIVE_TEXT_MAX_CHARS,
)


def representative_text(
    text: Any,
    max_chars: int = SEMANTIC_REPRESENTATIVE_TEXT_MAX_CHARS,
) -> str:
    """Return a stable, compact text window for finite-context embedding models.

    Proxy statements are much longer than stated-values pages. A fixed leading window keeps the
    embedding step deterministic and bounded while still capturing the core page or filing language
    available in the finalized source artifacts.
    """

    if text is None or (isinstance(text, float) and math.isnan(text)):
        return ""
    compact = " ".join(str(text).split())
    return compact[:max_chars]


def read_text_path(value: Any) -> str:
    """Read a clean-text artifact path, returning an empty string when unavailable.

    Part 2 stores large cleaned proxy text in sidecar files rather than the compact CSV. Missing
    paths are treated as unavailable evidence and reported through semantic status fields.
    """

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    path = Path(str(value))
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def semantic_status(
    part1_status: str,
    part2_status: str,
    stated_text: str,
    disclosure_text: str,
) -> tuple[str, str]:
    """Classify whether semantic text similarity can be computed."""

    part1_missing = part1_status != "usable"
    part2_missing = part2_status != "collected"
    if part1_missing and part2_missing:
        return "source_not_available", "Part 1 is not usable and Part 2 is not collected."
    if part1_missing:
        return "missing_part1_text", "Part 1 stated-values clean text is unavailable."
    if part2_missing:
        return "missing_part2_text", "Part 2 proxy clean text is unavailable."
    if not stated_text and not disclosure_text:
        return "missing_both_text", "Neither side has clean text available for embedding."
    if not stated_text:
        return "missing_part1_text", "Part 1 stated-values clean text is unavailable."
    if not disclosure_text:
        return "missing_part2_text", "Part 2 proxy clean text is unavailable."
    return "computed", ""


def cosine_from_vectors(left: Any, right: Any) -> float:
    """Return cosine similarity scaled by 100 for two numeric vectors."""

    dot = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(float(a) ** 2 for a in left))
    right_norm = math.sqrt(sum(float(b) ** 2 for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return round(100 * dot / (left_norm * right_norm), 6)


def _base_semantic_frame(part1_path: Path, part2_path: Path) -> pd.DataFrame:
    """Build the 450-row semantic eligibility frame before loading the embedding model."""

    part1 = pd.read_csv(part1_path)
    part2 = pd.read_csv(part2_path)
    merged = part1.merge(part2, on=["ticker", "year"], suffixes=("_part1", "_part2"))
    if len(merged) != 450:
        raise ValueError(f"Expected 450 merged company-years, found {len(merged)}")

    records: list[dict[str, Any]] = []
    for row in merged.to_dict("records"):
        # The eligibility pass is model-free. This makes status accounting reproducible and lets
        # validation distinguish source gaps from embedding/runtime failures.
        stated_text = representative_text(row.get("page_text_clean"))
        disclosure_text = representative_text(read_text_path(row.get("text_path")))
        status, gap_reason = semantic_status(
            str(row.get("observation_status") or ""),
            str(row.get("collection_status") or ""),
            stated_text,
            disclosure_text,
        )
        records.append(
            {
                "ticker": row["ticker"],
                "year": int(row["year"]),
                "semantic_similarity_status": status,
                "semantic_similarity_gap_reason": gap_reason,
                "semantic_embedding_model": (
                    SEMANTIC_EMBEDDING_MODEL if status == "computed" else ""
                ),
                "stated_representative_text": stated_text,
                "disclosure_representative_text": disclosure_text,
            }
        )
    return pd.DataFrame(records).sort_values(["ticker", "year"]).reset_index(drop=True)


def build_semantic_similarity(
    part1_path: Path = PART1_DATASET,
    part2_path: Path = PART2_DATASET,
    *,
    model_name: str = SEMANTIC_EMBEDDING_MODEL,
) -> pd.DataFrame:
    """Build pairwise Part 1/Part 2 semantic similarity for all company-years."""

    frame = _base_semantic_frame(part1_path, part2_path)
    frame["semantic_text_similarity"] = None
    computed = frame["semantic_similarity_status"] == "computed"
    if computed.any():
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        stated_texts = frame.loc[computed, "stated_representative_text"].tolist()
        disclosure_texts = frame.loc[computed, "disclosure_representative_text"].tolist()
        # The model is asked for normalized vectors, but cosine_from_vectors still computes the
        # denominator explicitly so the helper remains correct in tests with ordinary vectors.
        embeddings = model.encode(
            stated_texts + disclosure_texts,
            batch_size=16,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        split = len(stated_texts)
        similarities = [
            cosine_from_vectors(stated_vector, disclosure_vector)
            for stated_vector, disclosure_vector in zip(
                embeddings[:split],
                embeddings[split:],
                strict=True,
            )
        ]
        frame.loc[computed, "semantic_text_similarity"] = similarities
        frame.loc[computed, "semantic_embedding_model"] = model_name

    return frame[
        [
            "ticker",
            "year",
            "semantic_text_similarity",
            "semantic_similarity_status",
            "semantic_similarity_gap_reason",
            "semantic_embedding_model",
        ]
    ]


def write_semantic_similarity(
    output_path: Path = SEMANTIC_OUTPUT,
    part1_path: Path = PART1_DATASET,
    part2_path: Path = PART2_DATASET,
) -> pd.DataFrame:
    """Write the semantic similarity robustness output."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = build_semantic_similarity(part1_path, part2_path)
    frame.to_csv(output_path, index=False)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part1", type=Path, default=PART1_DATASET)
    parser.add_argument("--part2", type=Path, default=PART2_DATASET)
    parser.add_argument("--output", type=Path, default=SEMANTIC_OUTPUT)
    args = parser.parse_args()
    frame = write_semantic_similarity(args.output, args.part1, args.part2)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": len(frame),
                "semantic_status_counts": frame["semantic_similarity_status"]
                .value_counts()
                .sort_index()
                .to_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
