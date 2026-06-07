from org_auth_part2.figures import event_window_svg, sector_heatmap_svg, theme_over_time_svg


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

