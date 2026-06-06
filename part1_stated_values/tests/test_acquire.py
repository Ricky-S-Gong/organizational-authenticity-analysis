import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from org_auth_part1.acquire import build_annual_outputs
from org_auth_part1.discover import PageCandidate, candidate_cache_path
from org_auth_part1.models import CdxCapture


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def cache_record(
    cache_dir: Path,
    candidate: PageCandidate,
    captures: list[CdxCapture],
    *,
    year: int | None = None,
    status: str = "success",
) -> None:
    path = candidate_cache_path(cache_dir, candidate, year)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "collection_status": status,
                "attempt_count": 1,
                "year": year,
                "captures": [capture.model_dump(mode="json") for capture in captures],
            }
        )
    )


def test_builds_deterministic_annual_candidates_and_explicit_statuses(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidates.csv"
    target_path = tmp_path / "targets.csv"
    cache_dir = tmp_path / "cache"
    candidate_fields = [
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
    write_csv(
        candidate_path,
        candidate_fields,
        [
            {
                "ticker": "AAA",
                "candidate_url": "https://example.com/about",
                "page_type": "about",
                "valid_from_year": 2020,
                "valid_to_year": 2021,
                "eligibility_status": "approved",
            },
            {
                "ticker": "BBB",
                "candidate_url": "https://example.org/about",
                "page_type": "about",
                "valid_from_year": 2020,
                "valid_to_year": 2021,
                "eligibility_status": "approved",
            },
        ],
    )
    write_csv(
        target_path,
        ["ticker", "company_name", "sector", "year", "target_timestamp", "observation_status"],
        [
            {
                "ticker": ticker,
                "company_name": ticker,
                "sector": "Technology",
                "year": year,
                "target_timestamp": datetime(year, 6, 30, 12, tzinfo=UTC).isoformat(),
                "observation_status": "pending",
            }
            for ticker, year in [("AAA", 2020), ("AAA", 2021), ("BBB", 2020), ("CCC", 2020)]
        ],
    )
    aaa = PageCandidate(
        "AAA",
        "https://example.com/about",
        "https://example.com/about",
        "about",
        2020,
        2021,
        "approved",
    )
    bbb = PageCandidate(
        "BBB",
        "https://example.org/about",
        "https://example.org/about",
        "about",
        2020,
        2021,
        "approved",
    )
    cache_record(
        cache_dir,
        aaa,
        [
            CdxCapture(
                timestamp=datetime(2020, 7, 1, tzinfo=UTC),
                original_url=aaa.candidate_url,
                status_code=200,
                mime_type="text/html",
            ),
            CdxCapture(
                timestamp=datetime(2020, 6, 29, tzinfo=UTC),
                original_url=aaa.candidate_url,
                status_code=200,
                mime_type="text/html",
            ),
            CdxCapture(
                timestamp=datetime(2021, 6, 30, tzinfo=UTC),
                original_url=aaa.candidate_url,
                status_code=302,
                mime_type="text/html",
            ),
        ],
        year=2020,
    )
    cache_record(
        cache_dir,
        aaa,
        [
            CdxCapture(
                timestamp=datetime(2021, 6, 30, tzinfo=UTC),
                original_url=aaa.candidate_url,
                status_code=302,
                mime_type="text/html",
            ),
        ],
        year=2021,
    )
    cache_record(cache_dir, bbb, [], year=2020)

    candidates, statuses = build_annual_outputs(candidate_path, target_path, cache_dir)

    assert [row["capture_timestamp"] for row in candidates] == [
        "2020-07-01T00:00:00+00:00",
        "2020-06-29T00:00:00+00:00",
        "2021-06-30T00:00:00+00:00",
    ]
    assert candidates[0]["selected"] is True
    assert candidates[2]["eligible"] is False
    assert candidates[2]["rejection_reason"] == "status_code_302"
    assert [row["acquisition_status"] for row in statuses] == [
        "selected",
        "no_eligible_capture",
        "no_cdx_capture",
        "no_eligible_page",
    ]
    assert statuses[0]["selected_replay_url"].endswith("id_/https://example.com/about")
    assert statuses[0]["query_status"] == "complete"


def test_missing_cache_is_discovery_incomplete(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidates.csv"
    target_path = tmp_path / "targets.csv"
    write_csv(
        candidate_path,
        [
            "ticker",
            "candidate_url",
            "page_type",
            "valid_from_year",
            "valid_to_year",
            "discovery_method",
            "eligibility_status",
            "eligibility_reason",
            "reviewer",
        ],
        [
            {
                "ticker": "AAA",
                "candidate_url": "https://example.com/about",
                "page_type": "about",
                "valid_from_year": 2020,
                "valid_to_year": 2020,
                "eligibility_status": "approved",
            }
        ],
    )
    write_csv(
        target_path,
        ["ticker", "company_name", "sector", "year", "target_timestamp", "observation_status"],
        [
            {
                "ticker": "AAA",
                "company_name": "AAA",
                "sector": "Technology",
                "year": 2020,
                "target_timestamp": "2020-06-30T12:00:00+00:00",
                "observation_status": "pending",
            }
        ],
    )

    _, statuses = build_annual_outputs(candidate_path, target_path, tmp_path / "cache")

    assert statuses[0]["acquisition_status"] == "discovery_incomplete"


def test_failed_year_cache_does_not_pollute_successful_adjacent_year(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidates.csv"
    target_path = tmp_path / "targets.csv"
    cache_dir = tmp_path / "cache"
    fields = [
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
    write_csv(
        candidate_path,
        fields,
        [
            {
                "ticker": "AAA",
                "candidate_url": "https://example.com/about",
                "page_type": "about",
                "valid_from_year": 2020,
                "valid_to_year": 2021,
                "eligibility_status": "approved",
            }
        ],
    )
    write_csv(
        target_path,
        ["ticker", "company_name", "sector", "year", "target_timestamp", "observation_status"],
        [
            {
                "ticker": "AAA",
                "company_name": "AAA",
                "sector": "Technology",
                "year": year,
                "target_timestamp": datetime(year, 6, 30, 12, tzinfo=UTC).isoformat(),
                "observation_status": "pending",
            }
            for year in (2020, 2021)
        ],
    )
    candidate = PageCandidate(
        "AAA",
        "https://example.com/about",
        "https://example.com/about",
        "about",
        2020,
        2021,
        "approved",
    )
    cache_record(cache_dir, candidate, [], year=2020, status="failed")
    cache_record(
        cache_dir,
        candidate,
        [
            CdxCapture(
                timestamp=datetime(2021, 6, 30, tzinfo=UTC),
                original_url=candidate.candidate_url,
                status_code=200,
                mime_type="text/html",
            )
        ],
        year=2021,
    )

    _, statuses = build_annual_outputs(candidate_path, target_path, cache_dir)

    assert [row["acquisition_status"] for row in statuses] == [
        "discovery_incomplete",
        "selected",
    ]
