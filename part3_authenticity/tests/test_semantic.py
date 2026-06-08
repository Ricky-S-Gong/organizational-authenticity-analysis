from __future__ import annotations

from org_auth_part3.semantic import cosine_from_vectors, representative_text, semantic_status


def test_representative_text_compacts_and_truncates() -> None:
    text = " alpha\n\n beta   gamma "

    assert representative_text(text, max_chars=12) == "alpha beta g"


def test_semantic_status_rules() -> None:
    assert semantic_status("usable", "collected", "a", "b")[0] == "computed"
    assert semantic_status("missing", "missing", "", "")[0] == "source_not_available"
    assert semantic_status("missing", "collected", "", "b")[0] == "missing_part1_text"
    assert semantic_status("usable", "missing", "a", "")[0] == "missing_part2_text"
    assert semantic_status("usable", "collected", "", "")[0] == "missing_both_text"
    assert semantic_status("usable", "collected", "a", "")[0] == "missing_part2_text"


def test_cosine_from_vectors_scales_to_100() -> None:
    assert cosine_from_vectors([1, 0], [1, 0]) == 100
    assert cosine_from_vectors([1, 0], [0, 1]) == 0
