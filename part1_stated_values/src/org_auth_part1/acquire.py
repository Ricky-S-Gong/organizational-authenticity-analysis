"""Build deterministic annual Wayback candidate and acquisition-status outputs."""

import argparse
import csv
import json
import re
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

REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
HTML_MIME_TYPES = {"text/html", "application/xhtml+xml"}
ASSET_OR_DOCUMENT_URL = re.compile(
    r"(?:/media/|/images?/|/assets?/|/static/|/~/media/|"
    r"\.(?:ashx|css|gif|ico|jpe?g|js|pdf|png|svg|webp)(?:[?#]|$))",
    re.IGNORECASE,
)
PRIMARY_STATED_VALUE_TERMS = (
    "mission",
    "values",
    "purpose",
    "vision",
    "who-we-are",
    "who_we_are",
    "company-overview",
    "company_overview",
    "overview",
    "about-us",
    "about_us",
    "aboutus",
    "about/",
)
SECONDARY_STATED_VALUE_TERMS = (
    "default.aspx",
    "backgrounder",
    "factsheet",
    "fact-sheet",
    "company-information",
)
LOW_VALUE_SUBPAGE_TERMS = (
    "awards",
    "board",
    "management",
    "officer",
    "executive",
    "governance",
    "corpgov",
    "history",
    "foundation",
    "research",
    "/rd/",
    "refiner",
    "where-we-operate",
    "investor",
    "shareholder",
    "stockholder",
    "media",
    "press",
    "news",
    "privacy",
    "terms",
)


def is_likely_asset_or_document_url(url: str) -> bool:
    """Reject captures that are clearly files/assets rather than narrative pages."""
    return bool(ASSET_OR_DOCUMENT_URL.search(url))


def stated_values_capture_priority(
    candidate: PageCandidate, capture: CdxCapture
) -> tuple[int, int]:
    """Prefer broad stated-values pages over narrow historical subpages.

    CDX often returns many technically valid captures for the same company-year. The
    first score favors pages that are likely to state organizational identity directly
    (mission, values, purpose, about). The second score penalizes pages that are
    usually narrower governance, investor, media, or history subpages.
    """
    text = f"{candidate.page_type} {candidate.candidate_url} {capture.original_url}".lower()
    if any(term in text for term in PRIMARY_STATED_VALUE_TERMS):
        positive = 0
    elif any(term in text for term in SECONDARY_STATED_VALUE_TERMS):
        positive = 1
    else:
        positive = 2

    negative = sum(term in text for term in LOW_VALUE_SUBPAGE_TERMS)
    return positive, negative


def rank_annual_captures(
    captures: list[CdxCapture], target_timestamp: datetime
) -> list[CdxCapture]:
    """Return eligible same-year captures ranked nearest to the target timestamp."""
    eligible = [
        capture
        for capture in captures
        if capture.year == target_timestamp.year
        and capture.is_html_success()
        and not is_likely_asset_or_document_url(capture.original_url)
    ]
    return sorted(
        eligible,
        key=lambda capture: (
            abs(capture.timestamp - target_timestamp),
            capture.timestamp,
            capture.original_url,
        ),
    )


def is_replayable_capture(capture: CdxCapture) -> bool:
    """Return whether a capture is worth replaying when no direct 200 HTML capture exists.

    Redirect and WARC revisit rows can still replay into valid historical HTML through
    Wayback, so they are kept as recovery candidates. Asset/document URLs are excluded
    because they are outside the stated-values page scope.
    """
    if capture.is_html_success():
        return not is_likely_asset_or_document_url(capture.original_url)
    if is_likely_asset_or_document_url(capture.original_url):
        return False
    if capture.status_code in REDIRECT_STATUS_CODES and capture.mime_type in HTML_MIME_TYPES:
        return True
    return capture.mime_type == "warc/revisit"


def rank_replayable_captures(
    captures: list[CdxCapture], target_timestamp: datetime
) -> list[CdxCapture]:
    """Rank same-year captures that may replay to substantive HTML."""
    successful = rank_annual_captures(captures, target_timestamp)
    if successful:
        return successful
    fallback = [
        capture
        for capture in captures
        if capture.year == target_timestamp.year and is_replayable_capture(capture)
    ]
    return sorted(
        fallback,
        key=lambda capture: (
            abs(capture.timestamp - target_timestamp),
            capture.status_code not in REDIRECT_STATUS_CODES,
            capture.timestamp,
            capture.original_url,
        ),
    )


def select_annual_capture(
    captures: list[CdxCapture], target_timestamp: datetime
) -> CdxCapture | None:
    ranked = rank_replayable_captures(captures, target_timestamp)
    return ranked[0] if ranked else None


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


def _year_record(cache_dir: Path, candidate: PageCandidate, year: int) -> dict[str, Any] | None:
    """Load the per-year CDX cache, with read-only support for older aggregate caches."""
    record = load_cached_record(cache_dir, candidate, year)
    if record is not None:
        return record

    legacy = load_cached_record(cache_dir, candidate)
    if legacy is None or legacy.get("collection_status") != "success":
        return legacy
    captures = [capture for capture in _parse_captures(legacy) if capture.year == year]
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
    """Create an auditable ranked candidate table for one company-year.

    Every same-year capture is kept in the output with its rank, eligibility, and
    rejection reason. This lets a reviewer reconstruct why the selected replay URL
    was chosen without re-running CDX discovery.
    """
    ranked = sorted(
        candidates,
        key=lambda pair: (
            not pair[1].is_html_success(),
            stated_values_capture_priority(pair[0], pair[1]),
            abs(pair[1].timestamp - target_timestamp),
            pair[1].timestamp,
            pair[1].original_url,
            pair[0].normalized_url,
        ),
    )
    selected_rank = next(
        (
            rank
            for rank, (_candidate, capture) in enumerate(ranked, start=1)
            if is_replayable_capture(capture)
        ),
        None,
    )
    rows = []
    for rank, (candidate, capture) in enumerate(ranked, start=1):
        eligible = is_replayable_capture(capture)
        if eligible:
            rejection_reason = ""
        elif is_likely_asset_or_document_url(capture.original_url):
            rejection_reason = "asset_or_document_url"
        elif capture.status_code != 200:
            rejection_reason = f"status_code_{capture.status_code}"
        else:
            rejection_reason = f"non_html_mime_type_{capture.mime_type}"
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
                "selected": selected_rank is not None and rank == selected_rank,
            }
        )
    return rows


def build_annual_outputs(
    candidates_path: Path,
    targets_path: Path,
    cache_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build candidate-level and company-year acquisition outputs from cached CDX data.

    This step is intentionally offline: it reads only the deterministic target grid,
    approved/generated candidate registry, and CDX cache files. Network access happens
    in discovery, not during annual selection, which keeps selection reproducible.
    """
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
            if rank_replayable_captures([capture], target_timestamp)
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
                "query_status": ("complete" if relevant and not failed_or_missing else "incomplete")
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
