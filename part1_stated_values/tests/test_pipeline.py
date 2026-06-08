import json
from types import SimpleNamespace

import httpx
import requests
from org_auth_part1 import pipeline
from org_auth_part1.pipeline import (
    _raw_path,
    build_final_rows,
    build_text_artifacts,
    effective_fetch_target_keys,
    is_usable_artifact,
    merge_final_rows,
    merge_text_artifacts,
    meta_refresh_replay_url,
    redirect_replay_url,
    replay_url_variants,
    same_timestamp_replay_url,
)


def test_replay_fetch_uses_curl_after_python_clients_fail(monkeypatch) -> None:
    def fail_httpx(*_args: object, **_kwargs: object) -> None:
        raise httpx.ConnectError("blocked")

    def fail_requests(*_args: object, **_kwargs: object) -> None:
        raise requests.ConnectionError("blocked")

    def fake_curl(command: list[str], **_kwargs: object) -> SimpleNamespace:
        assert command[0] == "curl"
        return SimpleNamespace(
            returncode=0,
            stderr=b"",
            stdout=(
                b"<main>Our purpose is to serve patients with integrity and innovation.</main>"
                b"\n__ORG_AUTH_CURL_HTTP_CODE__:200"
                b"\n__ORG_AUTH_CURL_EFFECTIVE_URL__:https://web.archive.org/web/example"
            ),
        )

    monkeypatch.setattr(pipeline.httpx, "get", fail_httpx)
    monkeypatch.setattr(pipeline.requests, "get", fail_requests)
    monkeypatch.setattr(pipeline.subprocess, "run", fake_curl)

    response, client = pipeline._get_replay_response(
        "https://web.archive.org/web/example",
        timeout_seconds=10,
        headers={"User-Agent": "test-agent"},
    )

    assert client == "curl"
    assert response.status_code == 200
    assert b"serve patients" in response.content


def test_build_text_artifacts_extracts_fetched_html() -> None:
    status = [{"ticker": "MSFT", "year": "2024"}]
    fetches = {
        ("MSFT", 2024): {
            "fetch_status": "success",
            "content": (
                b"<main><h1>Our mission</h1>"
                b"<p>We serve customers with integrity and innovation.</p></main>"
            ),
        }
    }

    artifacts = build_text_artifacts(status, fetches)

    assert len(artifacts) == 1
    assert "integrity" in artifacts[0]["page_text_clean"]
    assert artifacts[0]["extraction_backend"] == "htmlparser"


def test_final_rows_keep_explicit_gap_reason() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "no_cdx_capture",
            "failure_reason": "no same-year CDX capture",
            "selected_original_url": "",
            "selected_replay_url": "",
            "selected_capture_timestamp": "",
        }
    ]

    rows = build_final_rows(status, [], {})

    assert rows[0]["observation_status"] == "no_cdx_capture"
    assert rows[0]["gap_reason"] == "no same-year CDX capture"
    assert rows[0]["changed_from_prior"] is None


def test_failed_fetch_is_preserved_as_text_artifact() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_original_url": "https://example.com/about",
            "selected_replay_url": "https://web.archive.org/example",
            "selected_capture_timestamp": "2024-06-30T12:00:00+00:00",
        }
    ]
    fetches = {
        ("MSFT", 2024): {
            "fetch_status": "failed",
            "error": "HTTPStatusError: 503 Service Unavailable",
        }
    }

    artifacts = build_text_artifacts(status, fetches)
    rows = build_final_rows(status, artifacts, fetches)

    assert len(artifacts) == 1
    assert artifacts[0]["fetch_status"] == "failed"
    assert "retrieval_failed" in artifacts[0]["qa_flags"]
    assert rows[0]["observation_status"] == "retrieval_failed"
    assert "503" in rows[0]["gap_reason"]


def test_selected_row_without_artifact_has_explicit_gap_reason() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_original_url": "https://example.com/about",
            "selected_replay_url": "https://web.archive.org/example",
            "selected_capture_timestamp": "2024-06-30T12:00:00+00:00",
        }
    ]

    rows = build_final_rows(status, [], {})

    assert rows[0]["observation_status"] == "retrieval_failed"
    assert rows[0]["gap_reason"] == "no selected usable capture"


def test_short_extraction_is_not_marked_usable() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_original_url": "https://example.com/about",
            "selected_replay_url": "https://web.archive.org/example",
            "selected_capture_timestamp": "2024-06-30T12:00:00+00:00",
        }
    ]
    fetches = {("MSFT", 2024): {"fetch_status": "success", "content": b"<main>Short</main>"}}
    artifacts = build_text_artifacts(status, fetches)

    rows = build_final_rows(status, artifacts, fetches)

    assert rows[0]["observation_status"] == "insufficient_substantive_text"


def test_wayback_json_api_fallback_recovers_nextjs_shell_page(monkeypatch) -> None:
    status = [
        {
            "ticker": "NKE",
            "company_name": "Nike",
            "sector": "Consumer",
            "year": "2024",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_original_url": "https://about.nike.com/en/company",
            "selected_replay_url": (
                "https://web.archive.org/web/20240630025627id_/https://about.nike.com/en/company"
            ),
            "selected_capture_timestamp": "2024-06-30T02:56:27+00:00",
        }
    ]
    fetches = {
        ("NKE", 2024): {
            "fetch_status": "success",
            "content": b"<html><body><div id='__next'>Loading...</div></body></html>",
            "attempt_log": [{"url": "html", "status": "success"}],
        }
    }

    class Response:
        status_code = 200
        content = b"{}"
        url = "https://web.archive.org/web/20240414173937id_/https://api.about.nike.com/v1/company/landing"

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "data": {
                    "intro": (
                        "NIKE, Inc. is a growth company and the biggest champion for "
                        "athletes and sport. We design products, services, and experiences "
                        "for athletes around the world."
                    ),
                    "blocks": [
                        {
                            "body": (
                                "Our purpose is to move the world forward through the power "
                                "of sport, innovation, teamwork, community, inclusion, and "
                                "sustainable growth."
                            )
                        }
                    ],
                }
            }

    monkeypatch.setattr(pipeline.httpx, "get", lambda *args, **kwargs: Response())

    artifacts = build_text_artifacts(
        status,
        fetches,
        enable_wayback_json_api_fallback=True,
    )
    rows = build_final_rows(status, artifacts, fetches)

    assert rows[0]["observation_status"] == "usable"
    assert "move the world forward" in artifacts[0]["page_text_clean"]
    assert artifacts[0]["extraction_backend"] == "htmlparser+wayback_json_api"
    assert "wayback_json_api_fallback" in artifacts[0]["qa_flags"]
    attempt_log = json.loads(artifacts[0]["fetch_attempt_log"])
    assert attempt_log[-1]["kind"] == "json_api_fallback"
    assert "api.about.nike.com/v1/company/landing" in attempt_log[-1]["url"]


def test_review_flags_do_not_block_substantive_short_text() -> None:
    words = " ".join(f"word{number}" for number in range(40))
    artifact = {
        "ticker": "MSFT",
        "year": 2024,
        "fetch_status": "cached",
        "page_text_clean": words,
        "clean_word_count": 40,
        "qa_flags": '["short_text", "high_link_text_ratio", "no_main_region"]',
    }

    assert is_usable_artifact(artifact) is True


def test_blocking_flags_still_prevent_usable_status() -> None:
    artifact = {
        "ticker": "MSFT",
        "year": 2024,
        "fetch_status": "cached",
        "page_text_clean": "404 Page not found",
        "clean_word_count": 4,
        "qa_flags": '["short_text", "likely_error_page"]',
    }

    assert is_usable_artifact(artifact) is False


def test_fetch_one_retries_and_preserves_error_chain(monkeypatch, tmp_path) -> None:
    attempts = []

    def fail_get(url, **kwargs):
        attempts.append((url, kwargs))
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(pipeline, "_get_replay_response", fail_get)

    result = pipeline._fetch_one(
        {
            "ticker": "MSFT",
            "year": "2024",
            "selected_replay_url": "https://web.archive.org/web/20240630id_/example",
        },
        tmp_path,
        force=True,
        timeout_seconds=1.0,
        retries=3,
        backoff_seconds=0.0,
        sleep=lambda seconds: None,
    )

    assert len(attempts) == 9
    assert result["fetch_status"] == "failed"
    assert len(result["errors"]) == 9
    assert "ConnectError" in result["error"]
    assert len(result["attempt_log"]) == 9


def test_replay_url_variants_try_raw_iframe_and_standard_replay() -> None:
    assert replay_url_variants(
        "https://web.archive.org/web/20240630id_/https://example.com/about"
    ) == [
        "https://web.archive.org/web/20240630id_/https://example.com/about",
        "https://web.archive.org/web/20240630if_/https://example.com/about",
        "https://web.archive.org/web/20240630/https://example.com/about",
    ]


def test_meta_refresh_replay_url_resolves_relative_target() -> None:
    replay = (
        "https://web.archive.org/web/20160712003937id_/"
        "http://www.goldmansachs.com/our-firm/progress/index.html"
    )
    html = (
        '<html><head><meta http-equiv="refresh" '
        'content="0;url=/who-we-are/progress/index.html"></head></html>'
    )

    assert meta_refresh_replay_url(replay, html) == (
        "https://web.archive.org/web/20160712003937id_/"
        "http://www.goldmansachs.com/who-we-are/progress/index.html"
    )


def test_meta_refresh_replay_url_ignores_noscript_refresh() -> None:
    replay = "https://web.archive.org/web/20201121005443id_/https://www.citigroup.com/citi/about/"
    html = (
        "<html><head><noscript>"
        '<meta http-equiv="refresh" content="0; URL=/citi/noscript.html" />'
        "</noscript></head><body><h1>About Citi</h1></body></html>"
    )

    assert meta_refresh_replay_url(replay, html) is None


def test_same_timestamp_replay_url_resolves_redirect_location() -> None:
    replay = "https://web.archive.org/web/20210512110850id_/https://www.citigroup.com/citi/about/"

    assert same_timestamp_replay_url(replay, "/citi/about/citi-at-a-glance.html") == (
        "https://web.archive.org/web/20210512110850id_/"
        "https://www.citigroup.com/citi/about/citi-at-a-glance.html"
    )


def test_redirect_replay_url_keeps_live_redirect_inside_wayback() -> None:
    replay = "https://web.archive.org/web/20210512110850id_/https://www.citigroup.com/citi/about/"
    response = httpx.Response(
        302,
        headers={"location": "https://www.citigroup.com/global/about-us"},
        request=httpx.Request("GET", replay),
    )

    assert redirect_replay_url(replay, response) == (
        "https://web.archive.org/web/20210512110850id_/https://www.citigroup.com/global/about-us"
    )


def test_fetch_one_falls_back_to_iframe_replay_variant(monkeypatch, tmp_path) -> None:
    calls = []

    class Response:
        status_code = 200
        content = b"<main>fallback content with enough words for logging</main>"
        url = "https://web.archive.org/web/20240630if_/https://example.com/about"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if "id_/" in url:
            raise httpx.ConnectError("connection refused")
        return Response(), "httpx"

    monkeypatch.setattr(pipeline, "_get_replay_response", fake_get)

    result = pipeline._fetch_one(
        {
            "ticker": "MSFT",
            "year": "2024",
            "selected_replay_url": "https://web.archive.org/web/20240630id_/https://example.com/about",
        },
        tmp_path,
        force=True,
        timeout_seconds=1.0,
        retries=3,
        backoff_seconds=0.0,
        sleep=lambda seconds: None,
    )

    assert result["fetch_status"] == "success"
    assert result["fetched_url"].endswith("if_/https://example.com/about")
    assert len(calls) == 2
    assert result["attempt_log"][0]["status"] == "failed"
    assert result["attempt_log"][1]["status"] == "success"


def test_fetch_one_follows_archived_meta_refresh(monkeypatch, tmp_path) -> None:
    calls = []

    class Response:
        status_code = 200

        def __init__(self, url, content):
            self.url = url
            self.content = content

        def raise_for_status(self) -> None:
            return None

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith("/our-firm/progress/index.html"):
            return (
                Response(
                    url,
                    (
                        b'<html><head><meta http-equiv="refresh" '
                        b'content="0;url=/who-we-are/progress/index.html"></head></html>'
                    ),
                ),
                "httpx",
            )
        return (
            Response(
                url,
                (
                    b"<main>We serve clients with integrity, excellence, teamwork, "
                    b"and long-term thinking.</main>"
                ),
            ),
            "httpx",
        )

    monkeypatch.setattr(pipeline, "_get_replay_response", fake_get)

    result = pipeline._fetch_one(
        {
            "ticker": "GS",
            "year": "2016",
            "selected_replay_url": (
                "https://web.archive.org/web/20160712003937id_/"
                "http://www.goldmansachs.com/our-firm/progress/index.html"
            ),
        },
        tmp_path,
        force=True,
        timeout_seconds=1.0,
        retries=1,
        backoff_seconds=0.0,
        sleep=lambda seconds: None,
    )

    assert result["fetch_status"] == "success"
    assert result["content"].startswith(b"<main>")
    assert result["attempt_log"][0]["status"] == "meta_refresh"
    assert "/who-we-are/progress/index.html" in calls[1]


def test_fetch_one_follows_archived_redirect_without_live_site(monkeypatch, tmp_path) -> None:
    calls = []
    source = "https://web.archive.org/web/20210512110850id_/https://www.citigroup.com/citi/about/"
    target = (
        "https://web.archive.org/web/20210512110850id_/https://www.citigroup.com/global/about-us"
    )

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if url == source:
            return (
                httpx.Response(
                    302,
                    headers={"location": "https://www.citigroup.com/global/about-us"},
                    request=httpx.Request("GET", url),
                ),
                "httpx",
            )
        return (
            httpx.Response(
                200,
                content=(
                    b"<main>Citi serves clients with responsible finance, simplicity, "
                    b"ingenuity, and global progress.</main>"
                ),
                request=httpx.Request("GET", url),
            ),
            "httpx",
        )

    monkeypatch.setattr(pipeline, "_get_replay_response", fake_get)

    result = pipeline._fetch_one(
        {
            "ticker": "C",
            "year": "2021",
            "selected_replay_url": source,
        },
        tmp_path,
        force=True,
        timeout_seconds=1.0,
        retries=1,
        backoff_seconds=0.0,
        sleep=lambda seconds: None,
    )

    assert result["fetch_status"] == "success"
    assert result["attempt_log"][0]["status"] == "archived_redirect"
    assert calls[1][0] == target


def test_fetch_one_uses_requests_fallback_after_httpx_connect_error(monkeypatch, tmp_path) -> None:
    replay_url = "https://web.archive.org/web/20240630id_/https://example.com/about"

    def fail_httpx_get(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    class Response:
        status_code = 200
        content = b"<main>Fallback content from requests with enough words to persist.</main>"
        url = replay_url
        headers = {}

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(pipeline.httpx, "get", fail_httpx_get)
    monkeypatch.setattr(pipeline.requests, "get", lambda *args, **kwargs: Response())

    response, client = pipeline._get_replay_response(
        replay_url,
        timeout_seconds=1.0,
        headers={"User-Agent": "test"},
    )

    assert response.content.startswith(b"<main>Fallback")
    assert client == "requests"


def test_fetch_one_keeps_existing_cache_when_forced_refresh_fails(monkeypatch, tmp_path) -> None:
    replay_url = "https://web.archive.org/web/20240630id_/https://example.com/about"
    raw_path = _raw_path(tmp_path, "MSFT", 2024, replay_url)
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(b"<main>cached text survives failed refresh</main>")

    monkeypatch.setattr(
        pipeline.httpx,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("refused")),
    )
    monkeypatch.setattr(
        pipeline.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("refused")),
    )

    result = pipeline._fetch_one(
        {
            "ticker": "MSFT",
            "year": "2024",
            "selected_replay_url": replay_url,
        },
        tmp_path,
        force=True,
        timeout_seconds=1.0,
        retries=1,
        backoff_seconds=0.0,
        sleep=lambda seconds: None,
    )

    assert result["fetch_status"] == "cached_after_failed_refresh"
    assert result["content"] == b"<main>cached text survives failed refresh</main>"
    assert result["attempt_log"][-1]["status"] == "cached_after_failed_refresh"


def test_merge_text_artifacts_replaces_only_target_keys() -> None:
    existing = [
        {"ticker": "AAA", "year": "2020", "page_text_clean": "keep"},
        {"ticker": "BBB", "year": "2020", "page_text_clean": "replace"},
    ]
    updates = [{"ticker": "BBB", "year": "2020", "page_text_clean": "new"}]

    merged = merge_text_artifacts(existing, updates, target_keys={("BBB", 2020)})

    assert merged == [
        {"ticker": "AAA", "year": "2020", "page_text_clean": "keep"},
        {"ticker": "BBB", "year": "2020", "page_text_clean": "new"},
    ]


def test_raw_cache_path_is_tied_to_replay_url(tmp_path) -> None:
    first = _raw_path(
        tmp_path,
        "BRK.B",
        2020,
        "https://web.archive.org/web/20200630id_/https://example.com/about",
    )
    second = _raw_path(
        tmp_path,
        "BRK.B",
        2020,
        "https://web.archive.org/web/20200715id_/https://example.com/about",
    )

    assert first != second
    assert first.parent == second.parent
    assert first.parent.name == "brk_b"


def test_merge_final_rows_preserves_non_target_usable_rows() -> None:
    existing = [
        {
            "ticker": "AAA",
            "year": "2020",
            "observation_status": "usable",
            "clean_text_sha256": "keep",
        },
        {
            "ticker": "BBB",
            "year": "2020",
            "observation_status": "retrieval_failed",
            "clean_text_sha256": "",
        },
    ]
    rebuilt = [
        {
            "ticker": "AAA",
            "year": "2020",
            "observation_status": "retrieval_failed",
            "clean_text_sha256": "",
        },
        {
            "ticker": "BBB",
            "year": "2020",
            "observation_status": "usable",
            "clean_text_sha256": "new",
        },
    ]

    merged = merge_final_rows(existing, rebuilt, target_keys={("BBB", 2020)})

    assert merged == [
        {
            "ticker": "AAA",
            "year": "2020",
            "observation_status": "usable",
            "clean_text_sha256": "keep",
        },
        {
            "ticker": "BBB",
            "year": "2020",
            "observation_status": "usable",
            "clean_text_sha256": "new",
        },
    ]


def test_effective_fetch_target_keys_includes_new_selected_rows_missing_artifacts() -> None:
    selected = {("AAA", 2020), ("BBB", 2020), ("CCC", 2020)}
    existing_artifacts = [
        {"ticker": "AAA", "year": "2020"},
    ]

    keys = effective_fetch_target_keys(
        selected,
        existing_artifacts,
        target_keys={("BBB", 2020)},
    )

    assert keys == {("BBB", 2020), ("CCC", 2020)}
