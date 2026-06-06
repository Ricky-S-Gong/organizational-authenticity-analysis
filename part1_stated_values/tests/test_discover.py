import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from org_auth_part1.discover import (
    PageCandidate,
    build_replay_url,
    candidate_cache_path,
    collect_candidate,
    discover_candidates,
    normalize_url,
    query_log_rows,
)
from org_auth_part1.models import CdxCapture


def write_candidates(path: Path) -> None:
    fieldnames = [
        "ticker",
        "candidate_url",
        "page_type",
        "valid_from_year",
        "valid_to_year",
        "discovery_method",
        "eligibility_status",
        "eligibility_reason",
        "reviewer",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            [
                {
                    "ticker": "AAA",
                    "candidate_url": "HTTPS://Example.COM:443/about/?utm_source=x&b=2&a=1#team",
                    "page_type": "about",
                    "valid_from_year": 2016,
                    "valid_to_year": 2024,
                    "eligibility_status": "approved",
                },
                {
                    "ticker": "BBB",
                    "candidate_url": "https://example.org/careers",
                    "page_type": "culture",
                    "valid_from_year": 2016,
                    "valid_to_year": 2024,
                    "eligibility_status": "review",
                },
            ]
        )


def test_normalize_url_and_replay_url() -> None:
    assert normalize_url("HTTPS://Example.COM:443/about/?utm_source=x&b=2&a=1#team") == (
        "https://example.com/about?a=1&b=2"
    )
    assert build_replay_url("20200630120000", "https://example.com/about") == (
        "https://web.archive.org/web/20200630120000id_/https://example.com/about"
    )


def test_collect_candidate_retries_then_caches_success(tmp_path: Path) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )
    attempts = []
    sleeps = []

    def query(url: str, **kwargs: object):
        attempts.append((url, kwargs))
        if len(attempts) < 3:
            raise RuntimeError("temporary failure")
        return [
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url=url,
                status_code=200,
                mime_type="text/html",
            )
        ], {"response_status": 200}

    record = collect_candidate(
        candidate,
        tmp_path,
        query=query,
        retries=3,
        backoff_seconds=0.5,
        sleep=sleeps.append,
        jitter=lambda: 0,
    )

    assert record["collection_status"] == "success"
    assert record["attempt_count"] == 3
    assert sleeps == [0.5, 1.0]
    assert attempts[0][1] == {
        "start_year": 2020,
        "end_year": 2020,
        "timeout_seconds": 90.0,
    }
    assert record["captures"][0]["replay_url"].endswith("id_/https://example.com/about")

    collect_candidate(candidate, tmp_path, query=lambda _: (_ for _ in ()).throw(AssertionError()))
    assert json.loads(candidate_cache_path(tmp_path, candidate).read_text())["attempt_count"] == 3


def test_discovery_skips_candidates_that_are_not_approved(tmp_path: Path) -> None:
    candidates = tmp_path / "page_candidates.csv"
    write_candidates(candidates)
    queried = []

    def query(url: str, **_: object):
        queried.append(url)
        return [], {"response_status": 200}

    records = discover_candidates(candidates, tmp_path / "cache", query=query, jitter=lambda: 0)

    assert len(records) == 1
    assert queried == ["HTTPS://Example.COM:443/about/?utm_source=x&b=2&a=1#team"] * 9


def test_discovery_isolates_failures_by_year(tmp_path: Path) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2021,
        eligibility_status="approved",
    )

    def query(url: str, *, start_year: int, end_year: int, timeout_seconds: float):
        assert start_year == end_year
        assert timeout_seconds == 90.0
        if start_year == 2020:
            raise RuntimeError("temporary outage")
        return [
            CdxCapture(
                timestamp=datetime(2021, 6, 30, 12, tzinfo=UTC),
                original_url=url,
                status_code=200,
                mime_type="text/html",
            )
        ], {"response_status": 200, "requested_at": "now"}

    record = collect_candidate(
        candidate,
        tmp_path,
        query=query,
        retries=1,
        sleep=lambda _: None,
        jitter=lambda: 0,
    )

    assert record["collection_status"] == "partial"
    by_year = {year_record["year"]: year_record for year_record in record["year_records"]}
    assert by_year[2020]["collection_status"] == "failed"
    assert by_year[2021]["collection_status"] == "success"
    assert len(by_year[2021]["captures"]) == 1


def test_query_log_rows_record_year_level_provenance(tmp_path: Path) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )
    record = {
        "ticker": candidate.ticker,
        "candidate_url": candidate.candidate_url,
        "normalized_url": candidate.normalized_url,
        "page_type": candidate.page_type,
        "valid_from_year": candidate.valid_from_year,
        "valid_to_year": candidate.valid_to_year,
        "eligibility_status": candidate.eligibility_status,
        "year_records": [
            {
                "ticker": "AAA",
                "candidate_url": candidate.candidate_url,
                "normalized_url": candidate.normalized_url,
                "year": 2020,
                "collection_status": "failed",
                "attempt_count": 2,
                "errors": ["ReadTimeout: slow", "HTTPStatusError: 503"],
                "captures": [],
            }
        ],
    }

    rows = query_log_rows([record], tmp_path)

    assert rows[0]["query_status"] == "failed"
    assert rows[0]["error_types"] == "HTTPStatusError;ReadTimeout"
    assert rows[0]["cache_path"].endswith("-2020.json")
