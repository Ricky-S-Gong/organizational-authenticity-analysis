import json
from pathlib import Path

from org_auth_part1.status import format_summary, load_progress_events, summarize_progress


def write_companies(path: Path) -> None:
    sectors = [
        "Technology",
        "Healthcare",
        "Financials",
        "Consumer Discretionary",
        "Energy",
    ]
    rows = ["ticker,company_name,sector,primary_domain,known_historical_domains"]
    for sector in sectors:
        for index in range(10):
            ticker = f"{sector[:1]}{index}".upper()
            rows.append(f"{ticker},Company {ticker},{sector},{ticker.lower()}.example,")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_run_status_counts_cached_success_and_failed_years(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    write_companies(companies)
    log = tmp_path / "progress.jsonl"
    events = [
        {
            "stage": "cdx_discovery",
            "status": "cached",
            "ticker": "T0",
            "year": 2016,
            "capture_count": 3,
            "timestamp": "2026-01-01T00:00:00+00:00",
        },
        {
            "stage": "cdx_discovery",
            "status": "success",
            "ticker": "T0",
            "year": 2017,
            "capture_count": 0,
            "timestamp": "2026-01-01T00:00:01+00:00",
        },
        {
            "stage": "cdx_discovery",
            "status": "failed",
            "ticker": "T0",
            "year": 2018,
            "capture_count": 0,
            "timestamp": "2026-01-01T00:00:02+00:00",
        },
    ]
    log.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

    summary = summarize_progress(load_progress_events(log), companies_path=companies)

    first_company = summary["companies"][0]
    assert first_company["ticker"] == "T0"
    assert first_company["years_completed"] == 3
    assert first_company["years_with_capture"] == 1
    assert first_company["years_zero_capture"] == 1
    assert first_company["years_failed_only"] == 1
    assert first_company["years_incomplete"] == 6
    assert summary["company_years_completed"] == 3


def test_format_summary_shows_company_level_progress(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    write_companies(companies)
    summary = summarize_progress([], companies_path=companies)

    output = format_summary(summary)

    assert "Companies completed: 0/50 (seen 0/50)" in output
    assert "ticker  years  capture zero failed incomplete" in output
    assert "T0      0/9" in output
