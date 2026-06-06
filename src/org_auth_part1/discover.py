"""Discover and cache Wayback CDX captures for approved page candidates."""

import argparse
import csv
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from org_auth_part1.cdx import query_cdx
from org_auth_part1.models import CdxCapture

DEFAULT_PAGE_CANDIDATES = Path("part1_stated_values/config/page_candidates.csv")
DEFAULT_CACHE_DIR = Path("part1_stated_values/data/interim/cdx")
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


@dataclass(frozen=True)
class PageCandidate:
    ticker: str
    candidate_url: str
    normalized_url: str
    page_type: str
    valid_from_year: int
    valid_to_year: int
    eligibility_status: str


def normalize_url(url: str) -> str:
    """Return a stable URL for matching and cache identity without changing content paths."""
    value = url.strip()
    if not value:
        raise ValueError("candidate_url must not be empty")
    if "://" not in value:
        value = f"https://{value}"

    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    if not hostname:
        raise ValueError(f"candidate_url has no hostname: {url!r}")

    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        hostname = f"{hostname}:{port}"

    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, hostname, path, query, ""))


def build_replay_url(timestamp: str, original_url: str) -> str:
    """Build a raw Wayback replay URL that minimizes archive-injected markup."""
    return f"https://web.archive.org/web/{timestamp}id_/{original_url}"


def load_page_candidates(path: Path) -> list[PageCandidate]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)
        candidates = [
            PageCandidate(
                ticker=row["ticker"].strip(),
                candidate_url=row["candidate_url"].strip(),
                normalized_url=normalize_url(row["candidate_url"]),
                page_type=row["page_type"].strip(),
                valid_from_year=int(row["valid_from_year"] or 2016),
                valid_to_year=int(row["valid_to_year"] or 2024),
                eligibility_status=row["eligibility_status"].strip().lower(),
            )
            for row in rows
            if row["ticker"].strip() and row["candidate_url"].strip()
        ]
    return sorted(candidates, key=lambda item: (item.ticker, item.normalized_url))


def is_eligible_candidate(candidate: PageCandidate) -> bool:
    return candidate.eligibility_status in {"approved", "eligible"}


def candidate_cache_path(cache_dir: Path, candidate: PageCandidate) -> Path:
    identity = f"{candidate.ticker}\n{candidate.normalized_url}".encode()
    digest = hashlib.sha256(identity).hexdigest()[:16]
    return cache_dir / f"{candidate.ticker.lower()}-{digest}.json"


def _capture_payload(capture: CdxCapture) -> dict[str, Any]:
    payload = capture.model_dump(mode="json")
    payload["replay_url"] = build_replay_url(
        capture.timestamp.strftime("%Y%m%d%H%M%S"), capture.original_url
    )
    return payload


def collect_candidate(
    candidate: PageCandidate,
    cache_dir: Path,
    *,
    query: Callable[[str], tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    force: bool = False,
) -> dict[str, Any]:
    """Collect one candidate, reusing a completed cache record unless forced."""
    if retries < 1:
        raise ValueError("retries must be at least 1")
    cache_path = candidate_cache_path(cache_dir, candidate)
    if cache_path.exists() and not force:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("collection_status") == "success":
            return cached

    error_messages: list[str] = []
    for attempt in range(1, retries + 1):
        try:
            captures, query_metadata = query(candidate.candidate_url)
            record = {
                "ticker": candidate.ticker,
                "candidate_url": candidate.candidate_url,
                "normalized_url": candidate.normalized_url,
                "page_type": candidate.page_type,
                "valid_from_year": candidate.valid_from_year,
                "valid_to_year": candidate.valid_to_year,
                "eligibility_status": candidate.eligibility_status,
                "collection_status": "success",
                "attempt_count": attempt,
                "query": query_metadata,
                "captures": [_capture_payload(capture) for capture in captures],
            }
            break
        except Exception as exc:  # Network clients expose several retryable exception types.
            error_messages.append(f"{type(exc).__name__}: {exc}")
            if attempt < retries:
                sleep(backoff_seconds * (2 ** (attempt - 1)))
    else:
        record = {
            "ticker": candidate.ticker,
            "candidate_url": candidate.candidate_url,
            "normalized_url": candidate.normalized_url,
            "page_type": candidate.page_type,
            "valid_from_year": candidate.valid_from_year,
            "valid_to_year": candidate.valid_to_year,
            "eligibility_status": candidate.eligibility_status,
            "collection_status": "failed",
            "attempt_count": retries,
            "errors": error_messages,
            "captures": [],
        }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def discover_candidates(
    candidates_path: Path,
    cache_dir: Path,
    *,
    query: Callable[[str], tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    force: bool = False,
) -> list[dict[str, Any]]:
    records = []
    for candidate in load_page_candidates(candidates_path):
        if is_eligible_candidate(candidate):
            records.append(
                collect_candidate(
                    candidate,
                    cache_dir,
                    query=query,
                    retries=retries,
                    backoff_seconds=backoff_seconds,
                    sleep=sleep,
                    force=force,
                )
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_PAGE_CANDIDATES)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    records = discover_candidates(
        args.candidates,
        args.cache_dir,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        force=args.force,
    )
    succeeded = sum(record["collection_status"] == "success" for record in records)
    print(f"Collected {succeeded}/{len(records)} eligible page candidates")


if __name__ == "__main__":
    main()
