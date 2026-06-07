import json

from org_auth_part2.text_mining import (
    adjacent_theme_shifts,
    event_window_summary,
    theme_sector_summary,
    theme_year_summary,
)


def _row(ticker: str, sector: str, year: int, word_count: int, counts: dict[str, int]):
    return {
        "ticker": ticker,
        "company_name": ticker,
        "sector": sector,
        "year": year,
        "word_count": word_count,
        "sentence_count": 10,
        "theme_counts": counts,
        "linguistic_metrics": json.loads(
            '{"commitment_rate_per_100_words": 1.0, "average_sentence_length": 10}'
        ),
    }


def test_theme_year_summary_normalizes_by_words() -> None:
    rows = [
        _row("AAA", "Tech", 2020, 1000, {"integrity_and_ethics": 10}),
        _row("BBB", "Tech", 2020, 2000, {"integrity_and_ethics": 10}),
    ]
    summary = theme_year_summary(rows)
    target = next(
        row for row in summary if row["year"] == 2020 and row["theme_id"] == "integrity_and_ethics"
    )
    assert target["company_years"] == 2
    assert target["presence_rate"] == 1
    assert target["mean_matches_per_10k_words"] == 75


def test_theme_sector_summary_keeps_zero_presence() -> None:
    rows = [_row("AAA", "Tech", 2020, 1000, {})]
    summary = theme_sector_summary(rows)
    target = next(row for row in summary if row["theme_id"] == "integrity_and_ethics")
    assert target["presence_rate"] == 0
    assert target["mean_matches_per_10k_words"] == 0


def test_adjacent_theme_shifts_orders_by_absolute_change() -> None:
    rows = [
        _row("AAA", "Tech", 2020, 1000, {"integrity_and_ethics": 1}),
        _row("AAA", "Tech", 2021, 1000, {"integrity_and_ethics": 5}),
    ]
    shifts = adjacent_theme_shifts(rows)
    assert shifts[0]["theme_id"] == "integrity_and_ethics"
    assert shifts[0]["change_per_10k_words"] == 40


def test_event_window_summary_has_expected_windows() -> None:
    rows = [_row("AAA", "Tech", 2020, 1000, {"integrity_and_ethics": 1})]
    windows = {row["event_window"] for row in event_window_summary(rows)}
    assert "covid_dei_governance_window" in windows
    assert "pre_2020" in windows
