from __future__ import annotations

import json

from org_auth_part3.constants import THEME_IDS
from org_auth_part3.index import (
    cosine_alignment,
    jaccard_theme_overlap,
    l1_alignment,
    normalize_vector,
    overlap_alignment,
    parse_theme_vector,
    score_status,
)


def test_parse_theme_vector_returns_ordered_counts() -> None:
    payload = json.dumps(
        [
            {"theme_id": "customers_and_service", "match_count": 2},
            {"theme_id": "integrity_and_ethics", "match_count": "3"},
            {"theme_id": "unknown", "match_count": 99},
        ]
    )

    vector = parse_theme_vector(payload)

    assert set(vector) == set(THEME_IDS)
    assert vector["customers_and_service"] == 2
    assert vector["integrity_and_ethics"] == 3
    assert sum(vector.values()) == 5


def test_parse_theme_vector_handles_missing_and_malformed_values() -> None:
    assert sum(parse_theme_vector(None).values()) == 0
    assert sum(parse_theme_vector("").values()) == 0
    assert sum(parse_theme_vector("not-json").values()) == 0
    assert sum(parse_theme_vector("{}").values()) == 0


def test_normalize_vector_preserves_zero_vector() -> None:
    zero = {theme_id: 0 for theme_id in THEME_IDS}
    assert normalize_vector(zero) == {theme_id: 0.0 for theme_id in THEME_IDS}


def test_normalize_vector_sums_to_one_for_nonzero_vector() -> None:
    counts = {theme_id: 0 for theme_id in THEME_IDS}
    counts["customers_and_service"] = 1
    counts["integrity_and_ethics"] = 3

    shares = normalize_vector(counts)

    assert round(sum(shares.values()), 10) == 1
    assert shares["customers_and_service"] == 0.25
    assert shares["integrity_and_ethics"] == 0.75


def test_alignment_scores_for_identical_and_disjoint_distributions() -> None:
    a_counts = {theme_id: 0 for theme_id in THEME_IDS}
    b_counts = {theme_id: 0 for theme_id in THEME_IDS}
    a_counts["customers_and_service"] = 1
    b_counts["customers_and_service"] = 1
    a = normalize_vector(a_counts)
    b = normalize_vector(b_counts)

    assert overlap_alignment(a, b) == 100
    assert cosine_alignment(a, b) == 100
    assert l1_alignment(a, b) == 100
    assert jaccard_theme_overlap(a_counts, b_counts) == 100

    b_counts = {theme_id: 0 for theme_id in THEME_IDS}
    b_counts["integrity_and_ethics"] = 1
    b = normalize_vector(b_counts)

    assert overlap_alignment(a, b) == 0
    assert l1_alignment(a, b) == 0
    assert jaccard_theme_overlap(a_counts, b_counts) == 0


def test_score_status_rules() -> None:
    assert score_status("usable", "collected", 2, 2)[0] == "scored"
    assert score_status("no_cdx_capture", "missing", 0, 0)[0] == "missing_both"
    assert score_status("no_cdx_capture", "collected", 0, 5)[0] == "missing_part1"
    assert score_status("usable", "missing", 5, 0)[0] == "missing_part2"
    assert score_status("usable", "collected", 0, 5)[0] == "insufficient_stated_theme_signal"
    assert score_status("usable", "collected", 5, 0)[0] == (
        "insufficient_disclosure_theme_signal"
    )
