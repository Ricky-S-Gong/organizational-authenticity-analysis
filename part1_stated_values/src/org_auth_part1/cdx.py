"""Query and parse Wayback Machine CDX capture metadata."""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import requests

from org_auth_part1.models import CdxCapture

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
WAYBACK_AVAILABLE_ENDPOINT = "https://archive.org/wayback/available"
CDX_FIELDS = ["timestamp", "original", "statuscode", "mimetype", "digest", "length"]
WAYBACK_REPLAY_ORIGINAL = re.compile(r"/web/\d{14}(?:[a-z_]+)?/(.+)$")


def build_cdx_params(
    url: str,
    start_year: int = 2016,
    end_year: int = 2024,
    *,
    match_type: str = "exact",
) -> dict[str, str]:
    """Build official CDX API parameters for a bounded historical lookup."""
    params = {
        "url": url,
        "from": str(start_year),
        "to": str(end_year),
        "output": "json",
        "fl": ",".join(CDX_FIELDS),
        "collapse": "timestamp:8",
    }
    if match_type != "exact":
        params["matchType"] = match_type
    return params


def parse_optional_int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    return int(value)


def parse_cdx_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def parse_cdx_rows(payload: list[list[str]]) -> list[CdxCapture]:
    """Parse CDX JSON rows into validated capture records."""
    if not payload:
        return []
    header, *rows = payload
    missing_fields = set(CDX_FIELDS) - set(header)
    if missing_fields:
        raise ValueError(f"CDX response missing fields: {sorted(missing_fields)}")

    captures = []
    for row in rows:
        record = dict(zip(header, row, strict=True))
        captures.append(
            CdxCapture(
                timestamp=parse_cdx_timestamp(record["timestamp"]),
                original_url=record["original"],
                status_code=parse_optional_int(record["statuscode"]),
                mime_type=record["mimetype"] or None,
                digest=record["digest"] or None,
                length=parse_optional_int(record["length"]),
            )
        )
    return captures


def get_cdx_json(
    params: dict[str, str],
    *,
    timeout_seconds: float,
) -> tuple[list[list[str]], int, str]:
    """Fetch CDX JSON, falling back to requests for socket-level httpx failures."""
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(CDX_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json(), response.status_code, "httpx"
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
        response = requests.get(
            CDX_ENDPOINT,
            params=params,
            timeout=timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()
        return response.json(), response.status_code, "requests"


def query_cdx(
    url: str,
    *,
    start_year: int = 2016,
    end_year: int = 2024,
    timeout_seconds: float = 90.0,
    match_type: str = "exact",
) -> tuple[list[CdxCapture], dict[str, Any]]:
    """Query CDX and return both captures and request metadata for audit logs."""
    params = build_cdx_params(
        url,
        start_year=start_year,
        end_year=end_year,
        match_type=match_type,
    )
    payload, response_status, query_client = get_cdx_json(
        params,
        timeout_seconds=timeout_seconds,
    )
    return parse_cdx_rows(payload), {
        "endpoint": CDX_ENDPOINT,
        "params": params,
        "requested_at": datetime.now(UTC).isoformat(),
        "response_status": response_status,
        "query_client": query_client,
    }


def original_url_from_replay_url(replay_url: str, fallback_url: str) -> str:
    """Extract the archived original URL from a Wayback replay URL."""
    match = WAYBACK_REPLAY_ORIGINAL.search(replay_url)
    return match.group(1) if match else fallback_url


def query_wayback_available(
    url: str,
    *,
    target_year: int,
    timeout_seconds: float = 20.0,
) -> tuple[CdxCapture | None, dict[str, Any]]:
    """Query the official Wayback Availability JSON API for a same-year snapshot."""
    timestamp = f"{target_year}0630"
    params = {"url": url, "timestamp": timestamp}
    response = requests.get(
        WAYBACK_AVAILABLE_ENDPOINT,
        params=params,
        timeout=timeout_seconds,
        allow_redirects=True,
    )
    response.raise_for_status()
    payload = response.json()
    closest = payload.get("archived_snapshots", {}).get("closest", {})
    metadata = {
        "endpoint": WAYBACK_AVAILABLE_ENDPOINT,
        "params": params,
        "requested_at": datetime.now(UTC).isoformat(),
        "response_status": response.status_code,
        "query_client": "requests",
    }
    if not closest.get("available"):
        return None, metadata
    capture_timestamp = str(closest.get("timestamp", ""))
    if len(capture_timestamp) != 14:
        return None, metadata
    capture_time = datetime.strptime(capture_timestamp, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    if capture_time.year != target_year:
        return None, metadata
    status = int(closest.get("status") or 0)
    if status != 200:
        return None, metadata
    replay_url = str(closest.get("url", ""))
    return (
        CdxCapture(
            timestamp=capture_time,
            original_url=original_url_from_replay_url(replay_url, url),
            status_code=status,
            mime_type="text/html",
        ),
        metadata,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    captures, query_metadata = query_cdx(args.url)
    output = {
        "ticker": args.ticker,
        "query": query_metadata,
        "captures": [capture.model_dump(mode="json") for capture in captures],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {len(captures)} captures to {args.output}")


if __name__ == "__main__":
    main()
