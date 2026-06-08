from datetime import UTC, datetime

import httpx
import pytest
from org_auth_part1 import cdx
from org_auth_part1.cdx import (
    build_cdx_params,
    original_url_from_replay_url,
    parse_cdx_rows,
    query_cdx,
    query_wayback_available,
)


def test_build_cdx_params_preserves_discovery_information() -> None:
    params = build_cdx_params("https://example.com/about")

    assert params["from"] == "2016"
    assert params["to"] == "2024"
    assert "statuscode" in params["fl"]
    assert "filter" not in params


def test_build_cdx_params_can_slice_by_year() -> None:
    params = build_cdx_params("https://example.com/about", start_year=2020, end_year=2020)

    assert params["from"] == "2020"
    assert params["to"] == "2020"


def test_build_cdx_params_supports_prefix_match_type() -> None:
    params = build_cdx_params("https://example.com/about", match_type="prefix")

    assert params["matchType"] == "prefix"


def test_parse_cdx_rows() -> None:
    captures = parse_cdx_rows(
        [
            ["timestamp", "original", "statuscode", "mimetype", "digest", "length"],
            [
                "20200630123000",
                "https://example.com/about",
                "200",
                "text/html",
                "ABC123",
                "4567",
            ],
        ]
    )

    assert captures[0].timestamp == datetime(2020, 6, 30, 12, 30, tzinfo=UTC)
    assert captures[0].status_code == 200
    assert captures[0].length == 4567


def test_parse_cdx_rows_rejects_missing_fields() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        parse_cdx_rows([["timestamp", "original"]])


def test_query_cdx_falls_back_to_requests_after_httpx_connect_error(monkeypatch) -> None:
    class FailingClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            raise httpx.ConnectError("connection refused")

    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return [
                ["timestamp", "original", "statuscode", "mimetype", "digest", "length"],
                ["20200630120000", "https://example.com/about", "200", "text/html", "D", "12"],
            ]

    monkeypatch.setattr(cdx.httpx, "Client", FailingClient)
    monkeypatch.setattr(cdx.requests, "get", lambda *args, **kwargs: Response())

    captures, metadata = query_cdx("https://example.com/about", start_year=2020, end_year=2020)

    assert len(captures) == 1
    assert metadata["query_client"] == "requests"


def test_query_wayback_available_keeps_same_year_available_snapshot(monkeypatch) -> None:
    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "archived_snapshots": {
                    "closest": {
                        "available": True,
                        "status": "200",
                        "timestamp": "20200630120000",
                        "url": (
                            "http://web.archive.org/web/20200630120000/https://example.com/about"
                        ),
                    }
                }
            }

    monkeypatch.setattr(cdx.requests, "get", lambda *args, **kwargs: Response())

    capture, metadata = query_wayback_available(
        "https://example.com/about",
        target_year=2020,
    )

    assert capture is not None
    assert capture.original_url == "https://example.com/about"
    assert capture.mime_type == "text/html"
    assert metadata["query_client"] == "requests"


def test_query_wayback_available_rejects_cross_year_closest_snapshot(monkeypatch) -> None:
    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "archived_snapshots": {
                    "closest": {
                        "available": True,
                        "status": "200",
                        "timestamp": "20220714004253",
                        "url": (
                            "http://web.archive.org/web/20220714004253/https://example.com/about"
                        ),
                    }
                }
            }

    monkeypatch.setattr(cdx.requests, "get", lambda *args, **kwargs: Response())

    capture, _metadata = query_wayback_available("https://example.com/about", target_year=2020)

    assert capture is None


def test_original_url_from_replay_url_handles_wayback_modifiers() -> None:
    assert (
        original_url_from_replay_url(
            "https://web.archive.org/web/20200630120000id_/https://example.com/about",
            "https://fallback.test",
        )
        == "https://example.com/about"
    )
