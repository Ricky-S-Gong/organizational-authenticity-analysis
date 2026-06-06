"""Query and parse Wayback Machine CDX capture metadata."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from org_auth_part1.models import CdxCapture

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
CDX_FIELDS = ["timestamp", "original", "statuscode", "mimetype", "digest", "length"]


def build_cdx_params(url: str, start_year: int = 2016, end_year: int = 2024) -> dict[str, str]:
    return {
        "url": url,
        "from": str(start_year),
        "to": str(end_year),
        "output": "json",
        "fl": ",".join(CDX_FIELDS),
        "collapse": "timestamp:8",
    }


def parse_optional_int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    return int(value)


def parse_cdx_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def parse_cdx_rows(payload: list[list[str]]) -> list[CdxCapture]:
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


def query_cdx(
    url: str,
    *,
    start_year: int = 2016,
    end_year: int = 2024,
    timeout_seconds: float = 90.0,
) -> tuple[list[CdxCapture], dict[str, Any]]:
    params = build_cdx_params(url, start_year=start_year, end_year=end_year)
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = client.get(CDX_ENDPOINT, params=params)
        response.raise_for_status()
        payload = response.json()
    return parse_cdx_rows(payload), {
        "endpoint": CDX_ENDPOINT,
        "params": params,
        "requested_at": datetime.now(UTC).isoformat(),
        "response_status": response.status_code,
    }


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
