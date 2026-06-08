from __future__ import annotations

import pandas as pd
from org_auth_part4.analysis import (
    assign_terciles,
    build_diagnostics,
    case_audit_targets,
    composite_genre_pressure,
    count_phrase_matches,
    rate_per_1000_words,
)


def test_count_phrase_matches_case_punctuation_and_repeats() -> None:
    text = "Annual Meeting! annual meeting; proxy card. A vote, voting, and vote."
    assert count_phrase_matches(text, ["annual meeting", "proxy card", "vote"]) == 5


def test_count_phrase_matches_empty_text() -> None:
    assert count_phrase_matches("", ["annual meeting"]) == 0
    assert count_phrase_matches(None, ["annual meeting"]) == 0


def test_rate_per_1000_words_handles_zero_words() -> None:
    assert rate_per_1000_words(5, 0) == 0.0
    assert rate_per_1000_words(5, 1000) == 5.0


def test_composite_genre_pressure_handles_missing_rows() -> None:
    frame = pd.DataFrame(
        {
            "genre_status": ["computed", "computed", "missing_proxy_text"],
            "shareholder_mechanics_rate": [1.0, 3.0, 0.0],
            "governance_boilerplate_rate": [2.0, 4.0, 0.0],
            "legal_procedural_rate": [3.0, 5.0, 0.0],
        }
    )
    result = composite_genre_pressure(frame)
    assert result.iloc[0] < result.iloc[1]
    assert pd.isna(result.iloc[2])


def test_assign_terciles_labels_available_values() -> None:
    result = assign_terciles(pd.Series([1.0, 2.0, 3.0, None]))
    assert set(result.dropna()) == {"low", "medium", "high"}
    assert pd.isna(result.iloc[3])


def test_build_diagnostics_preserves_450_rows() -> None:
    diagnostics = build_diagnostics()
    assert len(diagnostics) == 450
    assert len(diagnostics.drop_duplicates(["ticker", "year"])) == 450
    assert (diagnostics["score_status"] == "scored").sum() == 328


def test_case_audit_targets_returns_expected_buckets() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D", "E", "F", "G", "H"],
            "company_name": ["A"] * 8,
            "sector": ["Tech"] * 8,
            "year": list(range(2016, 2024)),
            "authenticity_index": [10, 8, 80, 85, 9, 20, 75, 90],
            "semantic_0_100": [40, 40, 65, 90, 90, 92, 55, 40],
            "keyword_minus_semantic": [-30, -32, 15, -5, -81, -72, 20, 50],
            "proxy_genre_pressure": [3, -3, 3, 2.5, 3, 2.8, -2, 3.2],
            "genre_pressure_tercile": [
                "high",
                "low",
                "high",
                "high",
                "high",
                "high",
                "low",
                "high",
            ],
            "keyword_semantic_quadrant": ["both_low"] * 8,
        }
    )
    targets = case_audit_targets(frame, per_bucket=2)
    assert {
        "low_oai_low_ss",
        "low_oai_high_ss",
        "high_oai_low_ss",
        "high_oai_high_ss",
    }.issubset(set(targets["audit_bucket"]))
