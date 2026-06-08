from __future__ import annotations

import pandas as pd
from org_auth_part4.theme_semantic import (
    build_theme_semantic_summary,
    compact_excerpts,
    compute_theme_semantic_scores,
    parse_theme_evidence,
)


def test_parse_theme_evidence_extracts_excerpts() -> None:
    payload = """
    [
      {
        "theme_id": "employees_and_workplace",
        "match_count": 2,
        "evidence_excerpts": ["Employees build our culture.", "Workforce development."]
      }
    ]
    """
    parsed = parse_theme_evidence(payload)
    assert parsed["employees_and_workplace"]["match_count"] == 2
    assert len(parsed["employees_and_workplace"]["evidence_excerpts"]) == 2


def test_compact_excerpts_bounds_text() -> None:
    text = compact_excerpts(["a " * 100, "b " * 100], max_excerpts=1, max_chars=20)
    assert len(text) == 20
    assert "b" not in text


def test_compute_theme_semantic_scores_marks_missing_and_computed() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["A", "A"],
            "year": [2024, 2024],
            "theme_id": ["employees_and_workplace", "customers_and_service"],
            "score_status": ["scored", "scored"],
            "authenticity_index": [50.0, 50.0],
            "whole_text_semantic_similarity": [10.0, 10.0],
            "theme_semantic_status": ["pending", "missing_stated_theme_evidence"],
            "theme_semantic_similarity": [None, None],
            "theme_semantic_method": ["", ""],
            "stated_excerpt_count": [1, 0],
            "disclosure_excerpt_count": [1, 1],
            "stated_theme_match_count": [2, 0],
            "disclosure_theme_match_count": [2, 1],
            "stated_theme_share": [0.5, 0.0],
            "disclosure_theme_share": [0.5, 0.2],
            "stated_theme_excerpt_text": ["employees and workforce culture", ""],
            "disclosure_theme_excerpt_text": ["employees and workplace talent", "customers"],
        }
    )
    scored = compute_theme_semantic_scores(frame, model_name="definitely-not-a-real-model")
    assert scored.loc[0, "theme_semantic_similarity"] is not None
    assert scored.loc[0, "theme_semantic_status"] == "computed_tfidf_fallback"
    assert scored.loc[1, "theme_semantic_status"] == "missing_stated_theme_evidence"


def test_build_theme_semantic_summary_groups_by_theme() -> None:
    frame = pd.DataFrame(
        {
            "theme_id": ["a", "a", "b"],
            "theme_semantic_similarity": [10.0, 20.0, None],
            "theme_share_gap_abs": [0.1, 0.3, 0.2],
            "authenticity_index": [40.0, 50.0, 60.0],
        }
    )
    summary = build_theme_semantic_summary(frame)
    assert summary.iloc[0]["computed_company_years"] == 2
