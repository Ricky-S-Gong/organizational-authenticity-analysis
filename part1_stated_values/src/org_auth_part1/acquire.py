"""Build deterministic annual Wayback candidate and acquisition-status outputs."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from org_auth_part1.discover import (
    DEFAULT_CACHE_DIR,
    DEFAULT_PAGE_CANDIDATES,
    PageCandidate,
    build_replay_url,
    candidate_cache_path,
    is_eligible_candidate,
    load_page_candidates,
)
from org_auth_part1.models import CdxCapture
from org_auth_part1.select import rank_annual_captures

DEFAULT_TARGETS = Path("part1_stated_values/data/processed/target_company_years.csv")
DEFAULT_CANDIDATE_OUTPUT = Path("part1_stated_values/data/processed/annual_snapshot_candidates.csv")
DEFAULT_STATUS_OUTPUT = Path("part1_stated_values/data/processed/acquisition_status.csv")

CANDIDATE_FIELDS = [
    "ticker",
    "year",
    "target_timestamp",
    "candidate_url",
    "page_type",
    "capture_timestamp",
    "original_url",
    "replay_url",
    "status_code",
    "mime_type",
    "digest",
    "length",
    "distance_seconds",
    "rank",
    "eligible",
    "rejection_reason",
    "selected",
]
STATUS_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "year",
    "target_timestamp",
    "acquisition_status",
    "failure_reason",
    "eligible_page_count",
    "capture_count",
    "eligible_capture_count",
    "selected_capture_timestamp",
    "selected_original_url",
    "selected_replay_url",
    "query_status",
    "query_attempt_count",
]


def load_targets(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return sorted(
            csv.DictReader(file),
            key=lambda row: (row["ticker"], int(row["year"])),
        )


def load_cached_record(
    cache_dir: Path, candidate: PageCandidate, year: int | None = None
) -> dict[str, Any] | None:
    path = candidate_cache_path(cache_dir, candidate, year)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _parse_captures(record: dict[str, Any]) -> list[CdxCapture]:
    return [CdxCapture.model_validate(capture) for capture in record.get("captures", [])]


def _year_record(
    cache_dir: Path, candidate: PageCandidate, year: int
) -> dict[str, Any] | None:
    record = load_cached_record(cache_dir, candidate, year)
    if record is not None:
        return record

    legacy = load_cached_record(cache_dir, candidate)
    if legacy is None or legacy.get("collection_status") != "success":
        return legacy
    captures = [
        capture
        for capture in _parse_captures(legacy)
        if capture.year == year
    ]
    return {
        "ticker": candidate.ticker,
        "candidate_url": candidate.candidate_url,
        "normalized_url": candidate.normalized_url,
        "year": year,
        "collection_status": "success",
        "attempt_count": legacy.get("attempt_count", ""),
        "query": legacy.get("query", {}),
        "captures": [capture.model_dump(mode="json") for capture in captures],
    }


def _candidate_rows(
    ticker: str,
    year: int,
    target_timestamp: datetime,
    candidates: list[tuple[PageCandidate, CdxCapture]],
) -> list[dict[str, Any]]:
    ranked = sorted(
        candidates,
        key=lambda pair: (
            not pair[1].is_html_success(),
            abs(pair[1].timestamp - target_timestamp),
            pair[1].timestamp,
            pair[1].original_url,
            pair[0].normalized_url,
        ),
    )
    rows = []
    for rank, (candidate, capture) in enumerate(ranked, start=1):
        eligible = capture.is_html_success()
        if capture.status_code != 200:
            rejection_reason = f"status_code_{capture.status_code}"
        elif not eligible:
            rejection_reason = f"non_html_mime_type_{capture.mime_type}"
        else:
            rejection_reason = ""
        rows.append(
            {
                "ticker": ticker,
                "year": year,
                "target_timestamp": target_timestamp.isoformat(),
                "candidate_url": candidate.candidate_url,
                "page_type": candidate.page_type,
                "capture_timestamp": capture.timestamp.isoformat(),
                "original_url": capture.original_url,
                "replay_url": build_replay_url(
                    capture.timestamp.strftime("%Y%m%d%H%M%S"), capture.original_url
                ),
                "status_code": capture.status_code,
                "mime_type": capture.mime_type,
                "digest": capture.digest,
                "length": capture.length,
                "distance_seconds": int(abs(capture.timestamp - target_timestamp).total_seconds()),
                "rank": rank,
                "eligible": eligible,
                "rejection_reason": rejection_reason,
                "selected": eligible and rank == 1,
            }
        )
    return rows


def build_annual_outputs(
    candidates_path: Path,
    targets_path: Path,
    cache_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    page_candidates = load_page_candidates(candidates_path)
    candidates_by_ticker: dict[str, list[PageCandidate]] = {}
    for candidate in page_candidates:
        if is_eligible_candidate(candidate):
            candidates_by_ticker.setdefault(candidate.ticker, []).append(candidate)

    all_candidate_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for target in load_targets(targets_path):
        ticker = target["ticker"]
        year = int(target["year"])
        target_timestamp = datetime.fromisoformat(target["target_timestamp"])
        relevant = [
            candidate
            for candidate in candidates_by_ticker.get(ticker, [])
            if candidate.valid_from_year <= year <= candidate.valid_to_year
        ]
        cached = [(candidate, _year_record(cache_dir, candidate, year)) for candidate in relevant]
        successful = [
            (candidate, record)
            for candidate, record in cached
            if record is not None and record.get("collection_status") == "success"
        ]
        failed_or_missing = [
            (candidate, record)
            for candidate, record in cached
            if record is None or record.get("collection_status") != "success"
        ]
        captures = [
            (candidate, capture)
            for candidate, record in successful
            for capture in _parse_captures(record)
            if capture.year == year
        ]
        eligible = [
            (candidate, capture)
            for candidate, capture in captures
            if rank_annual_captures([capture], target_timestamp)
        ]
        rows = _candidate_rows(ticker, year, target_timestamp, captures)
        all_candidate_rows.extend(rows)
        selected_rows = [row for row in rows if row["selected"]]

        if selected_rows:
            acquisition_status, failure_reason = "selected", ""
            selected = selected_rows[0]
        elif not relevant:
            acquisition_status, failure_reason = "no_eligible_page", "no eligible page candidate"
            selected = {}
        elif failed_or_missing and not successful:
            acquisition_status = "discovery_incomplete"
            failure_reason = "same-year CDX query missing or failed for all relevant candidates"
            selected = {}
        elif failed_or_missing and not captures:
            acquisition_status = "discovery_incomplete"
            failure_reason = (
                "same-year CDX query incomplete and completed queries returned no captures"
            )
            selected = {}
        elif not captures:
            acquisition_status, failure_reason = "no_cdx_capture", "no same-year CDX capture"
            selected = {}
        else:
            acquisition_status = "no_eligible_capture"
            failure_reason = "same-year captures exist but none are successful HTML"
            selected = {}

        status_rows.append(
            {
                "ticker": ticker,
                "company_name": target["company_name"],
                "sector": target["sector"],
                "year": year,
                "target_timestamp": target_timestamp.isoformat(),
                "acquisition_status": acquisition_status,
                "failure_reason": failure_reason,
                "eligible_page_count": len(relevant),
                "capture_count": len(captures),
                "eligible_capture_count": len(eligible),
                "selected_capture_timestamp": selected.get("capture_timestamp", ""),
                "selected_original_url": selected.get("original_url", ""),
                "selected_replay_url": selected.get("replay_url", ""),
                "query_status": (
                    "complete" if relevant and not failed_or_missing else "incomplete"
                )
                if relevant
                else "not_applicable",
                "query_attempt_count": sum(
                    int(record.get("attempt_count") or 0)
                    for _, record in cached
                    if record is not None
                ),
            }
        )
    return all_candidate_rows, status_rows


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_PAGE_CANDIDATES)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--candidate-output", type=Path, default=DEFAULT_CANDIDATE_OUTPUT)
    parser.add_argument("--status-output", type=Path, default=DEFAULT_STATUS_OUTPUT)
    args = parser.parse_args()

    candidate_rows, status_rows = build_annual_outputs(
        args.candidates, args.targets, args.cache_dir
    )
    write_csv(candidate_rows, args.candidate_output, CANDIDATE_FIELDS)
    write_csv(status_rows, args.status_output, STATUS_FIELDS)
    print(f"Wrote {len(candidate_rows)} candidates and {len(status_rows)} annual statuses")


if __name__ == "__main__":
    main()
