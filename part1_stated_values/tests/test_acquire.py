import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from org_auth_part1.acquire import (
    build_annual_outputs,
    is_likely_asset_or_document_url,
    rank_annual_captures,
    select_annual_capture,
    stated_values_capture_priority,
)
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


def capture(timestamp: str, status_code: int = 200, mime_type: str = "text/html") -> CdxCapture:
    return CdxCapture(
        timestamp=datetime.fromisoformat(timestamp),
        original_url=f"https://example.com/about?capture={timestamp}",
        status_code=status_code,
        mime_type=mime_type,
    )


def test_selects_nearest_valid_same_year_capture() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)
    captures = [
        capture("2020-01-01T00:00:00+00:00"),
        capture("2020-07-01T00:00:00+00:00"),
        capture("2020-06-29T00:00:00+00:00"),
        capture("2021-06-30T12:00:00+00:00"),
        capture("2020-06-30T12:00:00+00:00", status_code=302),
    ]

    selected = select_annual_capture(captures, target)

    assert selected is not None
    assert selected.timestamp == datetime(2020, 7, 1, tzinfo=UTC)


def test_does_not_substitute_adjacent_year_capture() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)

    assert select_annual_capture([capture("2019-12-31T23:59:59+00:00")], target) is None


def test_tie_breaker_prefers_earlier_capture() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)
    captures = [
        capture("2020-07-01T12:00:00+00:00"),
        capture("2020-06-29T12:00:00+00:00"),
    ]

    ranked = rank_annual_captures(captures, target)

    assert ranked[0].timestamp == datetime(2020, 6, 29, 12, tzinfo=UTC)


def test_asset_urls_are_not_selected_as_replayable_pages() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)
    asset = CdxCapture(
        timestamp=datetime(2020, 6, 30, tzinfo=UTC),
        original_url="https://example.com/about/~/media/Images/about/logo_large.ashx",
        status_code=200,
        mime_type="text/html",
    )
    page = CdxCapture(
        timestamp=datetime(2020, 7, 5, tzinfo=UTC),
        original_url="https://example.com/about",
        status_code=200,
        mime_type="text/html",
    )

    selected = select_annual_capture([asset, page], target)

    assert is_likely_asset_or_document_url(asset.original_url) is True
    assert selected == page


def test_build_outputs_selects_first_eligible_capture_even_if_asset_ranks_first(
    tmp_path: Path,
) -> None:
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
                "target_timestamp": datetime(2020, 6, 30, 12, tzinfo=UTC).isoformat(),
                "observation_status": "pending",
            }
        ],
    )
    candidate = PageCandidate(
        "AAA",
        "https://example.com/about",
        "https://example.com/about",
        "about",
        2020,
        2020,
        "approved",
    )
    cache_record(
        cache_dir,
        candidate,
        [
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url="https://example.com/about/_layouts/ScriptResx.ashx",
                status_code=200,
                mime_type="text/html",
            ),
            CdxCapture(
                timestamp=datetime(2020, 7, 1, 12, tzinfo=UTC),
                original_url="https://example.com/about",
                status_code=200,
                mime_type="text/html",
            ),
        ],
        year=2020,
    )

    candidates, statuses = build_annual_outputs(candidate_path, target_path, cache_dir)

    assert candidates[0]["eligible"] is False
    assert candidates[0]["selected"] is False
    assert candidates[1]["eligible"] is True
    assert candidates[1]["selected"] is True
    assert statuses[0]["acquisition_status"] == "selected"
    assert statuses[0]["selected_original_url"] == "https://example.com/about"


def test_build_outputs_prefers_stated_values_page_over_low_value_subpage(
    tmp_path: Path,
) -> None:
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
                "target_timestamp": datetime(2020, 6, 30, 12, tzinfo=UTC).isoformat(),
                "observation_status": "pending",
            }
        ],
    )
    candidate = PageCandidate(
        "AAA",
        "https://example.com/about",
        "https://example.com/about",
        "about",
        2020,
        2020,
        "approved",
    )
    values_page = CdxCapture(
        timestamp=datetime(2020, 9, 1, 12, tzinfo=UTC),
        original_url="https://example.com/about/vision-and-values.aspx",
        status_code=200,
        mime_type="text/html",
    )
    awards_page = CdxCapture(
        timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
        original_url="https://example.com/about/awards.aspx",
        status_code=200,
        mime_type="text/html",
    )
    cache_record(cache_dir, candidate, [awards_page, values_page], year=2020)

    candidates, statuses = build_annual_outputs(candidate_path, target_path, cache_dir)

    assert stated_values_capture_priority(candidate, values_page) < stated_values_capture_priority(
        candidate, awards_page
    )
    assert candidates[0]["original_url"] == "https://example.com/about/vision-and-values.aspx"
    assert candidates[0]["selected"] is True
    assert statuses[0]["selected_original_url"] == (
        "https://example.com/about/vision-and-values.aspx"
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
    assert candidates[2]["eligible"] is True
    assert candidates[2]["rejection_reason"] == ""
    assert [row["acquisition_status"] for row in statuses] == [
        "selected",
        "selected",
        "no_cdx_capture",
        "no_eligible_page",
    ]
    assert statuses[0]["selected_replay_url"].endswith("id_/https://example.com/about")
    assert statuses[0]["query_status"] == "complete"
    assert statuses[1]["selected_replay_url"].endswith("id_/https://example.com/about")


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
