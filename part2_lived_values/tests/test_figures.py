from org_auth_part2.figures import (
    event_window_svg,
    language_tone_over_time_svg,
    sector_heatmap_svg,
    sector_tone_heatmap_svg,
    theme_over_time_svg,
)


def test_theme_over_time_svg_contains_svg_and_title() -> None:
    summary = {
        "top_overall_themes": [
            {"theme_id": "integrity_and_ethics", "theme_label": "Integrity and ethics"}
        ]
    }
    rows = [
        {
            "year": "2020",
            "theme_id": "integrity_and_ethics",
            "theme_label": "Integrity and ethics",
            "mean_matches_per_10k_words": "2.5",
        },
        {
            "year": "2021",
            "theme_id": "integrity_and_ethics",
            "theme_label": "Integrity and ethics",
            "mean_matches_per_10k_words": "3.5",
        },
    ]
    svg = theme_over_time_svg(rows, summary)
    assert svg.startswith("<svg")
    assert "Part 2 Theme Emphasis Over Time" in svg


def test_sector_heatmap_svg_contains_sector_label() -> None:
    summary = {
        "top_overall_themes": [
            {"theme_id": "integrity_and_ethics", "theme_label": "Integrity and ethics"}
        ]
    }
    rows = [
        {
            "sector": "Technology",
            "theme_id": "integrity_and_ethics",
            "theme_label": "Integrity and ethics",
            "mean_matches_per_10k_words": "7.0",
        }
    ]
    svg = sector_heatmap_svg(rows, summary)
    assert "Technology" in svg
    assert "7.0" in svg


def test_event_window_svg_contains_descriptive_note() -> None:
    summary = {
        "event_window_theme_changes": [
            {
                "theme_label": "Integrity and ethics",
                "window_minus_pre": 1.25,
            }
        ]
    }
    svg = event_window_svg(summary)
    assert "not a causal estimate" in svg
    assert "+1.25" in svg


def test_language_tone_over_time_svg_contains_index_note() -> None:
    rows = [
        {
            "year": "2020",
            "mean_first_person_plural_rate_per_100_words": "1.0",
            "mean_commitment_rate_per_100_words": "0.5",
            "mean_action_or_evidence_rate_per_100_words": "0.2",
            "mean_stakeholder_rate_per_100_words": "0.3",
        },
        {
            "year": "2021",
            "mean_first_person_plural_rate_per_100_words": "1.2",
            "mean_commitment_rate_per_100_words": "0.4",
            "mean_action_or_evidence_rate_per_100_words": "0.3",
            "mean_stakeholder_rate_per_100_words": "0.6",
        },
    ]
    svg = language_tone_over_time_svg(rows)
    assert "Part 2 Language and Tone Over Time" in svg
    assert "indexed" in svg


def test_sector_tone_heatmap_svg_contains_raw_rate_note() -> None:
    rows = [
        {
            "sector": "Technology",
            "mean_first_person_plural_rate_per_100_words": "1.8",
            "mean_commitment_rate_per_100_words": "0.4",
            "mean_action_or_evidence_rate_per_100_words": "0.1",
            "mean_stakeholder_rate_per_100_words": "0.25",
        },
        {
            "sector": "Energy",
            "mean_first_person_plural_rate_per_100_words": "1.3",
            "mean_commitment_rate_per_100_words": "0.3",
            "mean_action_or_evidence_rate_per_100_words": "0.2",
            "mean_stakeholder_rate_per_100_words": "0.30",
        },
    ]
    svg = sector_tone_heatmap_svg(rows)
    assert "Cross-Sector Language and Tone" in svg
    assert "labels show raw rates" in svg
