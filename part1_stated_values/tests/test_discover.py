import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from org_auth_part1.discover import (
    CANDIDATE_CSV_FIELDS,
    PageCandidate,
    build_replay_url,
    candidate_cache_path,
    collect_candidate,
    collect_candidate_year,
    discover_candidate_links_from_homepage,
    discover_candidates,
    discover_historical_page_candidates,
    discovered_url_score,
    homepage_variants_for_domain,
    merge_candidate_files,
    normalize_url,
    probe_url_variant_capture,
    query_log_rows,
    select_domain_discovered_urls,
    select_nearest_html_capture,
    select_url_variant_candidates,
    url_variants_for_historical_recovery,
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


def test_discovers_candidate_links_from_archived_homepage() -> None:
    html = """
    <html><body>
      <a href="/about-us/">About us</a>
      <a href="https://example.com/company/values?utm_source=archive">Our values</a>
      <a href="https://other.example.com/about">Other about</a>
      <a href="/products">Products</a>
      <a href="mailto:hello@example.com">Email</a>
    </body></html>
    """

    links = discover_candidate_links_from_homepage(html, "https://example.com/")

    assert links == [
        "https://example.com/about-us",
        "https://example.com/company/values",
    ]


def test_homepage_variants_are_conservative_and_deduped() -> None:
    assert homepage_variants_for_domain("example.com") == [
        "https://example.com/",
        "https://www.example.com/",
        "http://example.com/",
        "http://www.example.com/",
    ]


def test_url_variants_cover_common_historical_identity_paths() -> None:
    variants = url_variants_for_historical_recovery("https://example.com/company/about-us/")

    assert "http://example.com/company/about-us" in variants
    assert "http://www.example.com/company/about-us" in variants
    assert "https://www.example.com/company/about-us.html" in variants
    assert "https://www.example.com/who-we-are" not in variants
    assert all("utm_" not in item for item in variants)


def test_select_url_variant_candidates_limits_to_identity_like_urls() -> None:
    variants = select_url_variant_candidates(
        "https://example.com/products/widgets/",
        limit=4,
    )

    assert len(variants) == 4
    assert all(discovered_url_score(item) > 0 for item in variants)
    assert all(not item.endswith(".png") for item in variants)


def test_selects_nearest_successful_html_capture() -> None:
    captures = [
        CdxCapture(
            timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            original_url="https://example.com/",
            status_code=200,
            mime_type="text/html",
        ),
        CdxCapture(
            timestamp=datetime(2020, 7, 1, tzinfo=UTC),
            original_url="https://example.com/",
            status_code=200,
            mime_type="text/html; charset=utf-8",
        ),
        CdxCapture(
            timestamp=datetime(2020, 6, 30, tzinfo=UTC),
            original_url="https://example.com/file.pdf",
            status_code=200,
            mime_type="application/pdf",
        ),
    ]

    selected = select_nearest_html_capture(captures, 2020)

    assert selected is not None
    assert selected.timestamp == datetime(2020, 7, 1, tzinfo=UTC)


def test_domain_discovery_scores_identity_urls_above_assets() -> None:
    assert discovered_url_score("https://example.com/about-us") > 0
    assert discovered_url_score("https://example.com/assets/company-logo.png") == 0
    captures = [
        CdxCapture(
            timestamp=datetime(2020, 6, 1, tzinfo=UTC),
            original_url="https://example.com/news/company-award",
            status_code=200,
            mime_type="text/html",
        ),
        CdxCapture(
            timestamp=datetime(2020, 6, 1, tzinfo=UTC),
            original_url="https://example.com/who-we-are",
            status_code=200,
            mime_type="text/html",
        ),
    ]

    assert select_domain_discovered_urls(captures, max_candidates=1) == [
        "https://example.com/who-we-are"
    ]


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
    assert record["year_records"][0]["query_strategy"] == "exact"
    assert record["captures"][0]["replay_url"].endswith("id_/https://example.com/about")

    collect_candidate(candidate, tmp_path, query=lambda _: (_ for _ in ()).throw(AssertionError()))
    assert json.loads(candidate_cache_path(tmp_path, candidate).read_text())["attempt_count"] == 3


def test_collect_candidate_year_keeps_exact_zero_when_prefix_fails(tmp_path: Path) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )

    def query(url: str, **kwargs: object):
        if kwargs.get("match_type") == "prefix":
            raise RuntimeError("prefix CDX temporarily unavailable")
        return [], {"response_status": 200, "query_client": "test"}

    record = collect_candidate_year(
        candidate,
        2020,
        tmp_path,
        query=query,
        retries=1,
        jitter=lambda: 0,
    )

    assert record["collection_status"] == "success"
    assert record["query_strategy"] == "exact_prefix_failed"
    assert record["captures"] == []
    assert record["errors"][0].startswith("prefix_fallback_RuntimeError")


def test_discovery_skips_candidates_that_are_not_approved(tmp_path: Path) -> None:
    candidates = tmp_path / "page_candidates.csv"
    write_candidates(candidates)
    queried = []

    def query(url: str, **_: object):
        queried.append(url)
        return [], {"response_status": 200}

    records = discover_candidates(candidates, tmp_path / "cache", query=query, jitter=lambda: 0)

    assert len(records) == 1
    assert queried == ["HTTPS://Example.COM:443/about/?utm_source=x&b=2&a=1#team"] * 18


def test_merge_candidate_files_keeps_seed_and_adds_generated_rows(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    generated = tmp_path / "generated.csv"
    output = tmp_path / "augmented.csv"
    write_candidates(seed)
    with generated.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CANDIDATE_CSV_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "ticker": "AAA",
                "candidate_url": "https://example.com/company/values/",
                "page_type": "values",
                "valid_from_year": 2020,
                "valid_to_year": 2020,
                "discovery_method": "historical_homepage_link",
                "eligibility_status": "eligible",
                "eligibility_reason": "from homepage",
                "reviewer": "pipeline_historical_discovery",
            }
        )

    rows = merge_candidate_files(seed, generated, output)

    assert output.exists()
    assert len(rows) == 3
    assert any(row["candidate_url"] == "https://example.com/company/values/" for row in rows)


def test_historical_discovery_generates_audited_same_year_candidates(
    monkeypatch, tmp_path: Path
) -> None:
    companies = tmp_path / "companies.csv"
    companies.write_text(
        "ticker,company_name,sector,primary_domain,known_historical_domains\n"
        "AAA,Example,Technology,example.com,\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed.csv"
    write_candidates(seed)
    generated = tmp_path / "historical.csv"
    audit = tmp_path / "audit.csv"

    def query(url: str, **kwargs: object):
        assert kwargs["start_year"] == 2020
        if url != "https://example.com/":
            return [], {"response_status": 200}
        return [
            CdxCapture(
                timestamp=datetime(2020, 6, 29, 12, tzinfo=UTC),
                original_url=url,
                status_code=200,
                mime_type="text/html",
            )
        ], {"response_status": 200}

    class FakeResponse:
        text = '<a href="/company/values">Values</a><a href="/products">Products</a>'

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str) -> FakeResponse:
            assert "20200629120000id_" in url
            return FakeResponse()

    monkeypatch.setattr("org_auth_part1.discover.httpx.Client", FakeClient)
    monkeypatch.setattr(
        "org_auth_part1.discover.query_domain_identity_captures",
        lambda *args, **kwargs: ([], {"response_status": 200, "capture_count": 0}),
    )

    rows, audit_rows = discover_historical_page_candidates(
        companies,
        seed,
        generated,
        audit,
        target_keys={("AAA", 2020)},
        query=query,
    )

    homepage_rows = [row for row in rows if row["discovery_method"] == "historical_homepage_link"]
    variant_rows = [row for row in rows if row["discovery_method"] == "historical_url_variant"]

    assert homepage_rows == [
        {
            "ticker": "AAA",
            "candidate_url": "https://example.com/company/values",
            "page_type": "values",
            "valid_from_year": 2020,
            "valid_to_year": 2020,
            "discovery_method": "historical_homepage_link",
            "eligibility_status": "eligible",
            "eligibility_reason": (
                "Machine-discovered from same-year archived homepage link; "
                "audit before substantive interpretation."
            ),
            "reviewer": "pipeline_historical_discovery",
        }
    ]
    assert variant_rows
    assert all(row["discovery_method"] == "historical_url_variant" for row in variant_rows)
    assert len(audit_rows) == 4
    assert any(row["discovered_link_count"] == 1 for row in audit_rows)


def test_historical_discovery_can_generate_variants_without_homepage_fetch(
    monkeypatch, tmp_path: Path
) -> None:
    companies = tmp_path / "companies.csv"
    companies.write_text(
        "ticker,company_name,sector,primary_domain,known_historical_domains\n"
        "AAA,Example,Technology,example.com,\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed.csv"
    write_candidates(seed)

    def fail_client(*args: object, **kwargs: object) -> object:
        raise AssertionError("homepage fetch should be skipped")

    monkeypatch.setattr("org_auth_part1.discover.httpx.Client", fail_client)

    rows, audit_rows = discover_historical_page_candidates(
        companies,
        seed,
        tmp_path / "historical.csv",
        tmp_path / "audit.csv",
        target_keys={("AAA", 2020)},
        enable_homepage_link_discovery=False,
    )

    assert audit_rows == []
    assert rows
    assert {row["discovery_method"] for row in rows} == {"historical_url_variant"}


def test_historical_variant_generation_can_require_positive_cdx_probe(
    monkeypatch, tmp_path: Path
) -> None:
    companies = tmp_path / "companies.csv"
    companies.write_text(
        "ticker,company_name,sector,primary_domain,known_historical_domains\n"
        "AAA,Example,Technology,example.com,\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed.csv"
    write_candidates(seed)
    calls = []

    def query(url: str, **kwargs: object):
        calls.append((url, kwargs))
        if normalize_url(url) == "http://example.com/about":
            return [
                CdxCapture(
                    timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                    original_url=url,
                    status_code=200,
                    mime_type="text/html",
                )
            ], {"response_status": 200}
        return [], {"response_status": 200}

    monkeypatch.setattr(
        "org_auth_part1.discover.httpx.Client",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("homepage fetch should be skipped")
        ),
    )
    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (None, {"response_status": 200}),
    )

    rows, audit_rows = discover_historical_page_candidates(
        companies,
        seed,
        tmp_path / "historical.csv",
        tmp_path / "audit.csv",
        target_keys={("AAA", 2020)},
        query=query,
        enable_homepage_link_discovery=False,
        require_url_variant_cdx_capture=True,
    )

    assert [row["candidate_url"] for row in rows] == ["http://example.com/about"]
    assert all(row["discovery_method"] == "historical_url_variant" for row in rows)
    assert any(
        row["discovery_source"] == "url_variant_cdx_probe"
        and row["query_url"] == "http://example.com/about"
        and row["capture_count"] == 1
        for row in audit_rows
    )
    assert len(calls) == 4


def test_url_variant_probe_retries_transient_cdx_errors(monkeypatch) -> None:
    calls = []

    def query(url: str, **kwargs: object):
        calls.append((url, kwargs))
        if len(calls) == 1:
            raise TimeoutError("temporary CDX failure")
        return [
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url=url,
                status_code=200,
                mime_type="text/html",
            )
        ], {"response_status": 200}

    monkeypatch.setattr("org_auth_part1.discover.time.sleep", lambda seconds: None)

    captures, selected, metadata, error = probe_url_variant_capture(
        "http://example.com/about",
        2020,
        query=query,
        retries=2,
        backoff_seconds=0.1,
        sleep_seconds=0.1,
    )

    assert len(captures) == 1
    assert selected is not None
    assert metadata["attempt_count"] == 2
    assert "TimeoutError" in error
    assert len(calls) == 2


def test_url_variant_probe_can_use_availability_when_cdx_returns_no_captures(
    monkeypatch,
) -> None:
    monkeypatch.setattr("org_auth_part1.discover.time.sleep", lambda seconds: None)
    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url="https://example.com/about",
                status_code=200,
                mime_type="text/html",
            ),
            {"response_status": 200, "query_client": "requests"},
        ),
    )

    captures, selected, metadata, error = probe_url_variant_capture(
        "https://example.com/about",
        2020,
        query=lambda *args, **kwargs: ([], {"response_status": 200}),
        retries=1,
    )

    assert len(captures) == 1
    assert selected is not None
    assert metadata["query_client"] == "requests"
    assert error == ""


def test_url_variant_probe_can_use_availability_after_cdx_errors(monkeypatch) -> None:
    monkeypatch.setattr("org_auth_part1.discover.time.sleep", lambda seconds: None)
    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url="https://example.com/about",
                status_code=200,
                mime_type="text/html",
            ),
            {"response_status": 200, "query_client": "requests"},
        ),
    )

    captures, selected, metadata, error = probe_url_variant_capture(
        "https://example.com/about",
        2020,
        query=lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("CDX down")),
        retries=1,
    )

    assert len(captures) == 1
    assert selected is not None
    assert metadata["query_client"] == "requests"
    assert "ConnectionError" in error


def test_collect_candidate_year_can_use_wayback_availability_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )

    def query(url: str, **kwargs: object):
        return [], {"response_status": 200}

    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url="https://example.com/about",
                status_code=200,
                mime_type="text/html",
            ),
            {"response_status": 200, "query_client": "requests"},
        ),
    )

    record = collect_candidate_year(
        candidate,
        2020,
        tmp_path,
        query=query,
        retries=1,
        availability_fallback=True,
    )

    assert record["collection_status"] == "success"
    assert record["query_strategy"] == "availability_fallback"
    assert len(record["captures"]) == 1


def test_collect_candidate_year_revisits_zero_capture_cache_for_availability_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )
    cached = {
        "ticker": "AAA",
        "candidate_url": "https://example.com/about",
        "normalized_url": "https://example.com/about",
        "page_type": "about",
        "valid_from_year": 2020,
        "valid_to_year": 2020,
        "eligibility_status": "approved",
        "year": 2020,
        "collection_status": "success",
        "attempt_count": 1,
        "query_strategy": "prefix_fallback",
        "query": {"response_status": 200},
        "captures": [],
    }
    candidate_cache_path(tmp_path, candidate, 2020).write_text(
        json.dumps(cached),
        encoding="utf-8",
    )
    query_calls = []

    def query(url: str, **kwargs: object):
        query_calls.append(url)
        return [], {"response_status": 200}

    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url="https://example.com/about",
                status_code=200,
                mime_type="text/html",
            ),
            {"response_status": 200, "query_client": "requests"},
        ),
    )

    record = collect_candidate_year(
        candidate,
        2020,
        tmp_path,
        query=query,
        retries=1,
        availability_fallback=True,
    )

    assert query_calls == ["https://example.com/about", "https://example.com/about"]
    assert record["query_strategy"] == "availability_fallback"
    assert len(record["captures"]) == 1


def test_collect_candidate_year_uses_availability_after_cdx_error(
    monkeypatch, tmp_path: Path
) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )

    def query(url: str, **kwargs: object):
        raise ConnectionError("CDX unavailable")

    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (
            CdxCapture(
                timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                original_url="https://example.com/about",
                status_code=200,
                mime_type="text/html",
            ),
            {"response_status": 200, "query_client": "requests"},
        ),
    )

    record = collect_candidate_year(
        candidate,
        2020,
        tmp_path,
        query=query,
        retries=1,
        availability_fallback=True,
    )

    assert record["collection_status"] == "success"
    assert record["query_strategy"] == "availability_fallback_after_cdx_error"
    assert "ConnectionError" in record["errors"][0]
    assert len(record["captures"]) == 1


def test_collect_candidate_year_preserves_zero_capture_cache_when_fallback_finds_nothing(
    monkeypatch, tmp_path: Path
) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )
    cached = {
        "ticker": "AAA",
        "candidate_url": "https://example.com/about",
        "normalized_url": "https://example.com/about",
        "page_type": "about",
        "valid_from_year": 2020,
        "valid_to_year": 2020,
        "eligibility_status": "approved",
        "year": 2020,
        "collection_status": "success",
        "attempt_count": 1,
        "query_strategy": "prefix_fallback",
        "query": {"response_status": 200},
        "captures": [],
    }
    cache_path = candidate_cache_path(tmp_path, candidate, 2020)
    cache_path.write_text(json.dumps(cached), encoding="utf-8")

    def query(url: str, **kwargs: object):
        raise ConnectionError("CDX unavailable")

    monkeypatch.setattr(
        "org_auth_part1.discover.query_wayback_available",
        lambda *args, **kwargs: (None, {"response_status": 200, "query_client": "requests"}),
    )

    record = collect_candidate_year(
        candidate,
        2020,
        tmp_path,
        query=query,
        retries=1,
        availability_fallback=True,
    )

    assert record == cached
    assert json.loads(cache_path.read_text(encoding="utf-8")) == cached


def test_historical_variant_probe_reuses_completed_zero_capture_audit(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    companies.write_text(
        "ticker,company_name,sector,primary_domain,known_historical_domains\n"
        "AAA,Example,Technology,example.com,\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed.csv"
    write_candidates(seed)
    audit = tmp_path / "audit.csv"
    audit.write_text(
        "discovery_source,ticker,year,domain,query_url,homepage_url,query_status,"
        "capture_count,selected_capture_timestamp,selected_original_url,selected_replay_url,"
        "fetched,discovered_link_count,candidate_urls,error\n"
        "url_variant_cdx_probe,AAA,2020,example.com,http://example.com/about,,200,0,,,,"
        "False,0,[],\n",
        encoding="utf-8",
    )
    calls = []

    def query(url: str, **kwargs: object):
        calls.append(url)
        return [], {"response_status": 200}

    rows, audit_rows = discover_historical_page_candidates(
        companies,
        seed,
        tmp_path / "historical.csv",
        audit,
        target_keys={("AAA", 2020)},
        query=query,
        enable_homepage_link_discovery=False,
        require_url_variant_cdx_capture=True,
    )

    assert rows == []
    assert "http://example.com/about" not in calls
    assert len(audit_rows) == 4


def test_historical_discovery_generates_candidates_from_domain_cdx(
    monkeypatch, tmp_path: Path
) -> None:
    companies = tmp_path / "companies.csv"
    companies.write_text(
        "ticker,company_name,sector,primary_domain,known_historical_domains\n"
        "AAA,Example,Technology,example.com,\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed.csv"
    write_candidates(seed)
    generated = tmp_path / "historical.csv"
    audit = tmp_path / "audit.csv"

    monkeypatch.setattr(
        "org_auth_part1.discover.fetch_homepage_capture",
        lambda *args, **kwargs: (
            type("Fetch", (), {"html": "", "capture": None, "replay_url": "", "error": ""})(),
            {"response_status": 200, "capture_count": 0},
        ),
    )
    monkeypatch.setattr(
        "org_auth_part1.discover.query_domain_identity_captures",
        lambda *args, **kwargs: (
            [
                CdxCapture(
                    timestamp=datetime(2020, 6, 1, tzinfo=UTC),
                    original_url="https://example.com/who-we-are",
                    status_code=200,
                    mime_type="text/html",
                )
            ],
            {"response_status": 200, "capture_count": 1},
        ),
    )

    rows, audit_rows = discover_historical_page_candidates(
        companies,
        seed,
        generated,
        audit,
        target_keys={("AAA", 2020)},
        workers=1,
        enable_domain_cdx_discovery=True,
    )

    assert any(row["candidate_url"] == "https://example.com/who-we-are" for row in rows)
    assert any(row["discovery_source"] == "domain_cdx" for row in audit_rows)


def test_domain_cdx_generated_candidates_are_opt_in(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    companies.write_text(
        "ticker,company_name,sector,primary_domain,known_historical_domains\n"
        "AAA,Example,Technology,example.com,\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed.csv"
    write_candidates(seed)
    generated = tmp_path / "historical.csv"
    generated.write_text(
        "ticker,candidate_url,page_type,valid_from_year,valid_to_year,discovery_method,"
        "eligibility_status,eligibility_reason,reviewer\n"
        "AAA,https://example.com/who-we-are,about,2020,2020,historical_domain_cdx_url,"
        "eligible,old broad domain candidate,pipeline_historical_discovery\n",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.csv"

    rows, _audit_rows = discover_historical_page_candidates(
        companies,
        seed,
        generated,
        audit,
        target_keys={("AAA", 2020)},
        workers=1,
    )

    assert not any(row["discovery_method"] == "historical_domain_cdx_url" for row in rows)


def test_discovery_can_limit_to_target_keys(tmp_path: Path) -> None:
    candidates = tmp_path / "page_candidates.csv"
    write_candidates(candidates)
    queried = []

    def query(url: str, **kwargs: object):
        queried.append((url, kwargs["start_year"]))
        return [], {"response_status": 200}

    records = discover_candidates(
        candidates,
        tmp_path / "cache",
        query=query,
        jitter=lambda: 0,
        target_keys={("AAA", 2020)},
    )

    assert len(records) == 1
    assert queried == [
        ("HTTPS://Example.COM:443/about/?utm_source=x&b=2&a=1#team", 2020),
        ("HTTPS://Example.COM:443/about/?utm_source=x&b=2&a=1#team", 2020),
    ]
    assert [record["year"] for record in records[0]["year_records"]] == [2020]


def test_discovery_uses_prefix_fallback_when_exact_query_is_empty(tmp_path: Path) -> None:
    candidate = PageCandidate(
        ticker="AAA",
        candidate_url="https://example.com/about",
        normalized_url="https://example.com/about",
        page_type="about",
        valid_from_year=2020,
        valid_to_year=2020,
        eligibility_status="approved",
    )
    calls = []

    def query(url: str, **kwargs: object):
        calls.append(kwargs)
        if kwargs.get("match_type") == "prefix":
            return [
                CdxCapture(
                    timestamp=datetime(2020, 6, 30, 12, tzinfo=UTC),
                    original_url=f"{url}/",
                    status_code=200,
                    mime_type="text/html",
                )
            ], {"response_status": 200}
        return [], {"response_status": 200}

    record = collect_candidate(candidate, tmp_path, query=query, sleep=lambda _: None)

    year_record = record["year_records"][0]
    assert year_record["collection_status"] == "success"
    assert year_record["query_strategy"] == "prefix_fallback"
    assert calls == [
        {"start_year": 2020, "end_year": 2020, "timeout_seconds": 90.0},
        {
            "start_year": 2020,
            "end_year": 2020,
            "timeout_seconds": 90.0,
            "match_type": "prefix",
        },
    ]


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
        prefix_fallback=False,
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
                "query_strategy": "",
                "errors": ["ReadTimeout: slow", "HTTPStatusError: 503"],
                "captures": [],
            }
        ],
    }

    rows = query_log_rows([record], tmp_path)

    assert rows[0]["query_status"] == "failed"
    assert rows[0]["error_types"] == "HTTPStatusError;ReadTimeout"
    assert rows[0]["query_strategy"] == ""
    assert rows[0]["cache_path"].endswith("-2020.json")
