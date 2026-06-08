from org_auth_part1.analyze import (
    TAXONOMY_VERSION,
    analyze_records,
    analyze_text,
    classify_themes,
    linguistic_metrics,
)


def test_theme_classification_is_multilabel_and_evidence_backed() -> None:
    text = (
        "Our mission is to earn customer trust through integrity. "
        "We invest in sustainable innovation for our communities."
    )

    evidence = classify_themes(text)
    by_id = {item.theme_id: item for item in evidence}

    assert {"purpose_and_identity", "customers_and_service", "integrity_and_ethics"} <= set(by_id)
    assert "customer" in by_id["customers_and_service"].matched_phrases
    assert by_id["customers_and_service"].evidence_excerpts == (
        "Our mission is to earn customer trust through integrity.",
    )
    assert all(item.taxonomy_version == TAXONOMY_VERSION for item in evidence)


def test_theme_rules_do_not_match_inside_unrelated_words() -> None:
    ids = {item.theme_id for item in classify_themes("We customized a platform.")}

    assert "customers_and_service" not in ids


def test_linguistic_metrics_are_deterministic_and_handle_empty_text() -> None:
    metrics = linguistic_metrics("We will invest $25 million. Our teams delivered results.")

    assert metrics["word_count"] == 9
    assert metrics["sentence_count"] == 2
    assert metrics["first_person_plural_count"] == 2
    assert metrics["commitment_count"] == 1
    assert metrics["action_or_evidence_count"] == 2
    assert metrics["quantified_claim_count"] == 1
    assert linguistic_metrics("")["average_sentence_length"] == 0.0


def test_analyze_text_is_json_serializable_shape() -> None:
    result = analyze_text("Our values include integrity and collaboration.")

    assert result["taxonomy_version"] == TAXONOMY_VERSION
    assert result["theme_categories"] == [
        "integrity_and_ethics",
        "collaboration_and_partnership",
        "purpose_and_identity",
    ]
    assert result["theme_evidence"][0]["evidence_excerpts"]


def test_analyze_records_does_not_classify_missing_as_absent() -> None:
    analyzed = analyze_records(
        [
            {"ticker": "A", "collection_status": "usable", "page_text_clean": "Our mission."},
            {
                "ticker": "B",
                "collection_status": "no_cdx_capture",
                "page_text_clean": "",
            },
        ]
    )

    assert analyzed[0]["theme_categories"] == ["purpose_and_identity"]
    assert analyzed[1]["theme_categories"] is None
    assert analyzed[1]["linguistic_metrics"] is None
