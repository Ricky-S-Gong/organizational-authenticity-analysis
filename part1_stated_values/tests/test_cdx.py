from datetime import UTC, datetime

import pytest
from org_auth_part1.cdx import build_cdx_params, parse_cdx_rows


def test_build_cdx_params_preserves_discovery_information() -> None:
    params = build_cdx_params("https://example.com/about")

    assert params["from"] == "2016"
    assert params["to"] == "2024"
    assert "statuscode" in params["fl"]
    assert "filter" not in params


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
