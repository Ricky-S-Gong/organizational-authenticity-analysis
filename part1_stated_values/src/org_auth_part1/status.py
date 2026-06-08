"""Summarize resumable Part 1 run progress from the JSONL progress log."""

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from org_auth_part1.run import DEFAULT_PROGRESS_LOG
from org_auth_part1.targets import DEFAULT_COMPANIES, TARGET_YEARS, load_companies

COMPLETE_STATUSES = {"success", "cached", "failed"}
DATA_STATUSES = {"success", "cached"}


@dataclass(frozen=True)
class YearProgress:
    ticker: str
    year: int
    event_count: int
    status: str
    capture_count: int
    latest_status: str
    latest_timestamp: str


def load_progress_events(progress_log: Path) -> list[dict[str, Any]]:
    if not progress_log.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in progress_log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _year_status(events: list[dict[str, Any]]) -> tuple[str, int]:
    data_events = [event for event in events if event.get("status") in DATA_STATUSES]
    capture_count = max((int(event.get("capture_count") or 0) for event in data_events), default=0)
    if capture_count > 0:
        return "has_capture", capture_count
    if data_events:
        return "zero_capture", 0
    if any(event.get("status") == "failed" for event in events):
        return "failed_only", 0
    return "incomplete", 0


def summarize_progress(
    events: list[dict[str, Any]],
    *,
    companies_path: Path = DEFAULT_COMPANIES,
) -> dict[str, Any]:
    companies = load_companies(companies_path)
    tickers = [company.ticker for company in companies]
    target_years = list(TARGET_YEARS)

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    latest_event: dict[tuple[str, int], dict[str, Any]] = {}
    for event in events:
        if event.get("stage") != "cdx_discovery":
            continue
        ticker = event.get("ticker")
        year = event.get("year")
        if not ticker or year is None:
            continue
        key = (str(ticker), int(year))
        grouped[key].append(event)
        if event.get("status") in COMPLETE_STATUSES:
            previous = latest_event.get(key)
            if previous is None or str(event.get("timestamp", "")) >= str(
                previous.get("timestamp", "")
            ):
                latest_event[key] = event

    year_progress: dict[tuple[str, int], YearProgress] = {}
    for key, year_events in grouped.items():
        latest = latest_event.get(key) or max(
            year_events, key=lambda event: str(event.get("timestamp", ""))
        )
        status, capture_count = _year_status(year_events)
        year_progress[key] = YearProgress(
            ticker=key[0],
            year=key[1],
            event_count=len(year_events),
            status=status,
            capture_count=capture_count,
            latest_status=str(latest.get("status", "")),
            latest_timestamp=str(latest.get("timestamp", "")),
        )

    companies_summary = []
    for ticker in tickers:
        years = [year_progress.get((ticker, year)) for year in target_years]
        seen = [item for item in years if item is not None]
        has_capture = sum(item.status == "has_capture" for item in seen)
        zero_capture = sum(item.status == "zero_capture" for item in seen)
        failed_only = sum(item.status == "failed_only" for item in seen)
        incomplete = len(target_years) - len(seen)
        completed_years = has_capture + zero_capture + failed_only
        latest_seen = max(
            seen,
            key=lambda item: item.latest_timestamp,
            default=None,
        )
        companies_summary.append(
            {
                "ticker": ticker,
                "years_completed": completed_years,
                "years_expected": len(target_years),
                "years_with_capture": has_capture,
                "years_zero_capture": zero_capture,
                "years_failed_only": failed_only,
                "years_incomplete": incomplete,
                "latest_year": latest_seen.year if latest_seen else "",
                "latest_status": latest_seen.latest_status if latest_seen else "",
                "latest_timestamp": latest_seen.latest_timestamp if latest_seen else "",
            }
        )

    completed_companies = sum(
        row["years_completed"] == row["years_expected"] for row in companies_summary
    )
    started_companies = sum(row["years_completed"] > 0 for row in companies_summary)
    company_years_completed = sum(row["years_completed"] for row in companies_summary)
    company_years_expected = len(tickers) * len(target_years)
    return {
        "companies_seen": started_companies,
        "companies_completed": completed_companies,
        "companies_expected": len(tickers),
        "company_years_completed": company_years_completed,
        "company_years_expected": company_years_expected,
        "company_years_with_capture": sum(row["years_with_capture"] for row in companies_summary),
        "company_years_zero_capture": sum(row["years_zero_capture"] for row in companies_summary),
        "company_years_failed_only": sum(row["years_failed_only"] for row in companies_summary),
        "company_years_incomplete": sum(row["years_incomplete"] for row in companies_summary),
        "companies": companies_summary,
    }


def format_summary(summary: dict[str, Any]) -> str:
    lines = [
        (
            "Companies completed: "
            f"{summary['companies_completed']}/{summary['companies_expected']} "
            f"(seen {summary['companies_seen']}/{summary['companies_expected']})"
        ),
        (
            "Company-years completed: "
            f"{summary['company_years_completed']}/{summary['company_years_expected']} "
            f"| with capture {summary['company_years_with_capture']} "
            f"| zero capture {summary['company_years_zero_capture']} "
            f"| failed only {summary['company_years_failed_only']} "
            f"| incomplete {summary['company_years_incomplete']}"
        ),
        "",
        ("ticker  years  capture zero failed incomplete latest_year latest_status"),
    ]
    for row in summary["companies"]:
        lines.append(
            f"{row['ticker']:<6} "
            f"{row['years_completed']:>2}/{row['years_expected']:<2}   "
            f"{row['years_with_capture']:>2}      "
            f"{row['years_zero_capture']:>2}   "
            f"{row['years_failed_only']:>2}     "
            f"{row['years_incomplete']:>2}         "
            f"{str(row['latest_year']):<11} "
            f"{row['latest_status']}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--progress-log", type=Path, default=DEFAULT_PROGRESS_LOG)
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = summarize_progress(
        load_progress_events(args.progress_log),
        companies_path=args.companies,
    )
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_summary(summary))


if __name__ == "__main__":
    main()
