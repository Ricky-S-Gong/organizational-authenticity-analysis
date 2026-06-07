import json

from org_auth_part2.analyze import analysis_json, assign_themes, linguistic_metrics


def test_assign_themes_returns_evidence() -> None:
    themes = assign_themes(
        "Our board is committed to integrity and transparency. "
        "We support diversity, inclusion, employees, and communities."
    )
    ids = {theme.theme_id for theme in themes}
    assert "integrity_and_ethics" in ids
    assert "diversity_equity_and_inclusion" in ids
    assert all(theme.evidence_excerpts for theme in themes)


def test_linguistic_metrics_counts_words() -> None:
    metrics = linguistic_metrics("We committed to increased transparency in 2024.")
    assert metrics["word_count"] == 7
    assert metrics["commitment_count"] == 1
    assert metrics["quantified_claim_count"] == 1


def test_analysis_json_is_parseable() -> None:
    categories, evidence, metrics = analysis_json("Our purpose is integrity and innovation.")
    assert "purpose_and_identity" in json.loads(categories)
    assert json.loads(evidence)
    assert json.loads(metrics)["word_count"] == 6
