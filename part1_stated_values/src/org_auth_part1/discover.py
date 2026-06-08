"""Discover and cache Wayback CDX captures for approved page candidates."""

import argparse
import csv
import hashlib
import json
import random
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from org_auth_part1.cdx import (
    CDX_ENDPOINT,
    CDX_FIELDS,
    parse_cdx_rows,
    query_cdx,
    query_wayback_available,
)
from org_auth_part1.models import CdxCapture

DEFAULT_PAGE_CANDIDATES = Path("part1_stated_values/config/page_candidates.csv")
DEFAULT_CACHE_DIR = Path("part1_stated_values/data/interim/cdx")
DEFAULT_QUERY_LOG = Path("part1_stated_values/data/processed/cdx_query_log.csv")
DEFAULT_HISTORICAL_CANDIDATES = Path(
    "part1_stated_values/data/processed/historical_page_candidates.csv"
)
DEFAULT_HISTORICAL_DISCOVERY_AUDIT = Path(
    "part1_stated_values/data/processed/historical_url_discovery_audit.csv"
)
DEFAULT_AUGMENTED_PAGE_CANDIDATES = Path(
    "part1_stated_values/data/interim/augmented_page_candidates.csv"
)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
DISCOVERY_LINK_KEYWORDS = {
    "about",
    "company",
    "corporate",
    "mission",
    "purpose",
    "values",
    "who-we-are",
    "who we are",
}
DOMAIN_DISCOVERY_LIMIT = 5000
DOMAIN_DISCOVERY_MAX_CANDIDATES = 3
URL_VARIANT_DISCOVERY_MAX_CANDIDATES = 4
QUERY_LOG_FIELDS = [
    "ticker",
    "candidate_url",
    "normalized_url",
    "year",
    "query_status",
    "attempt_count",
    "capture_count",
    "response_status",
    "query_strategy",
    "requested_at",
    "error_types",
    "cache_path",
]
CANDIDATE_CSV_FIELDS = [
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
HISTORICAL_DISCOVERY_AUDIT_FIELDS = [
    "discovery_source",
    "ticker",
    "year",
    "domain",
    "query_url",
    "homepage_url",
    "query_status",
    "capture_count",
    "selected_capture_timestamp",
    "selected_original_url",
    "selected_replay_url",
    "fetched",
    "discovered_link_count",
    "candidate_urls",
    "error",
]
COMMON_IDENTITY_PATHS = [
    "/about",
    "/about-us",
    "/company",
    "/company/about",
    "/company/about-us",
    "/corporate",
    "/our-company",
    "/who-we-are",
]


@dataclass(frozen=True)
class PageCandidate:
    ticker: str
    candidate_url: str
    normalized_url: str
    page_type: str
    valid_from_year: int
    valid_to_year: int
    eligibility_status: str


@dataclass(frozen=True)
class HistoricalHomepageFetch:
    capture: CdxCapture | None
    replay_url: str
    html: str
    error: str = ""


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


def discover_candidate_links_from_homepage(html: str, homepage_url: str) -> list[str]:
    """Return likely identity/value links from an archived homepage HTML document."""
    homepage_host = urlsplit(normalize_url(homepage_url)).hostname
    soup = BeautifulSoup(html, "lxml")
    discovered: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        text = anchor.get_text(" ", strip=True).lower()
        absolute = normalize_url(urljoin(homepage_url, href))
        parts = urlsplit(absolute)
        if parts.hostname != homepage_host:
            continue
        haystack = f"{parts.path.lower()} {text}"
        if any(keyword in haystack for keyword in DISCOVERY_LINK_KEYWORDS):
            discovered.add(absolute)
    return sorted(discovered)


def page_type_from_discovered_url(url: str) -> str:
    """Classify a discovered historical URL into the small page-type vocabulary."""
    haystack = urlsplit(url).path.lower()
    if "values" in haystack or "principles" in haystack:
        return "values"
    if "mission" in haystack:
        return "mission"
    if "purpose" in haystack:
        return "purpose"
    if "who-we-are" in haystack or "who_we_are" in haystack:
        return "about"
    if "company" in haystack or "corporate" in haystack:
        return "about"
    return "about"


def discovered_url_score(url: str) -> int:
    """Score likely company-level identity/value URLs discovered from historical indexes."""
    parts = urlsplit(normalize_url(url))
    path = parts.path.lower()
    if re.search(r"\.(?:css|js|json|xml|png|jpe?g|gif|svg|pdf|ashx)(?:$|[?#])", path):
        return 0
    score = 0
    path_with_spaces = path.replace("-", " ").replace("_", " ")
    if "who we are" in path_with_spaces:
        score += 9
    for keyword in DISCOVERY_LINK_KEYWORDS:
        if keyword in path or keyword in path_with_spaces:
            score += 5
    if any(item in path for item in ("about-us", "aboutus", "company-info")):
        score += 4
    if len([part for part in path.split("/") if part]) <= 4:
        score += 2
    if any(item in path for item in ("news", "press", "careers", "investor", "privacy")):
        score -= 3
    return score


def homepage_variants_for_domain(domain: str) -> list[str]:
    """Return conservative homepage URL variants for historical Wayback lookup."""
    host = domain.strip().lower().removeprefix("http://").removeprefix("https://").strip("/")
    variants = [
        f"https://{host}/",
        f"https://www.{host}/" if not host.startswith("www.") else f"https://{host}/",
        f"http://{host}/",
        f"http://www.{host}/" if not host.startswith("www.") else f"http://{host}/",
    ]
    return list(dict.fromkeys(normalize_url(url) for url in variants))


def url_variants_for_historical_recovery(url: str) -> list[str]:
    """Return conservative URL variants for historical CDX recovery.

    This is the first line of defense for suspected wrong-URL cases: scheme, ``www``,
    trailing slash, and simple ``.html`` variants often explain missing historical
    captures without requiring broader web search.
    """
    normalized = normalize_url(url)
    parts = urlsplit(normalized)
    host = parts.hostname or ""
    if not host:
        return []
    hosts = [host]
    if host.startswith("www."):
        hosts.append(host.removeprefix("www."))
    else:
        hosts.append(f"www.{host}")
    schemes = ["https", "http"] if parts.scheme == "https" else ["http", "https"]
    path = parts.path if parts.path else "/"
    path_candidates = {path}
    if path != "/":
        path_candidates.add(path.rstrip("/"))
        path_candidates.add(f"{path.rstrip('/')}/")
        if "." not in Path(path).name:
            path_candidates.add(f"{path.rstrip('/')}.html")
    if discovered_url_score(normalized) <= 0:
        for common_path in COMMON_IDENTITY_PATHS:
            path_candidates.add(common_path)
            path_candidates.add(f"{common_path}/")
            path_candidates.add(f"{common_path}.html")

    variants = []
    for scheme in schemes:
        for variant_host in hosts:
            for variant_path in sorted(path_candidates):
                try:
                    variant = normalize_url(
                        urlunsplit((scheme, variant_host, variant_path, "", ""))
                    )
                except ValueError:
                    continue
                if variant != normalized:
                    variants.append(variant)
    return list(dict.fromkeys(variants))


def select_url_variant_candidates(url: str, *, limit: int) -> list[str]:
    """Pick a small set of URL variants most likely to be company identity pages."""
    variants = url_variants_for_historical_recovery(url)
    ranked = sorted(
        variants,
        key=lambda item: (
            -discovered_url_score(item),
            urlsplit(item).scheme != "http",
            len(urlsplit(item).path),
            item,
        ),
    )
    return ranked[:limit]


def select_nearest_html_capture(captures: list[CdxCapture], year: int) -> CdxCapture | None:
    """Pick the nearest same-year successful HTML capture to the Part 1 target date."""
    target = datetime(year, 6, 30, 12, tzinfo=UTC)
    eligible = [
        capture
        for capture in captures
        if capture.timestamp.year == year
        and capture.status_code == 200
        and (capture.mime_type or "").lower().startswith("text/html")
    ]
    if not eligible:
        return None
    return min(eligible, key=lambda capture: abs((capture.timestamp - target).total_seconds()))


def probe_url_variant_capture(
    variant: str,
    year: int,
    *,
    query: Callable[..., tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    timeout_seconds: float = 15.0,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    sleep_seconds: float = 0.0,
    availability_fallback: bool = True,
) -> tuple[list[CdxCapture], CdxCapture | None, dict[str, Any], str]:
    """Probe CDX for a URL variant with gentle retry/backoff for Wayback instability.

    The return value separates raw captures, the selected same-year HTML capture, CDX
    metadata, and accumulated errors so the discovery audit can show both failed and
    successful probes.
    """
    if retries < 1:
        raise ValueError("retries must be at least 1")

    errors: list[str] = []
    for attempt in range(1, retries + 1):
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        try:
            captures, metadata = query(
                variant,
                start_year=year,
                end_year=year,
                timeout_seconds=timeout_seconds,
            )
            selected = select_nearest_html_capture(captures, year)
            if selected is None and availability_fallback:
                try:
                    capture, availability_metadata = query_wayback_available(
                        variant,
                        target_year=year,
                        timeout_seconds=timeout_seconds,
                    )
                    if capture is not None:
                        return (
                            [capture],
                            capture,
                            {**availability_metadata, "attempt_count": attempt},
                            "; ".join(errors),
                        )
                except Exception as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")
            return (
                captures,
                selected,
                {**metadata, "attempt_count": attempt},
                "; ".join(errors),
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)

    if availability_fallback:
        try:
            capture, metadata = query_wayback_available(
                variant,
                target_year=year,
                timeout_seconds=timeout_seconds,
            )
            if capture is not None:
                return [capture], capture, {**metadata, "attempt_count": retries}, "; ".join(errors)
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return [], None, {"response_status": "failed", "attempt_count": retries}, "; ".join(errors)


def fetch_homepage_capture(
    homepage_url: str,
    year: int,
    *,
    query: Callable[..., tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    timeout_seconds: float = 60.0,
) -> tuple[HistoricalHomepageFetch, dict[str, Any]]:
    """Find and fetch one archived homepage capture for historical link discovery.

    Archived homepages are used only to discover same-domain identity/value links; the
    downstream CDX/replay steps still validate whether those links have same-year text.
    """
    captures, query_metadata = query(
        homepage_url,
        start_year=year,
        end_year=year,
        timeout_seconds=timeout_seconds,
    )
    query_metadata = {**query_metadata, "capture_count": len(captures)}
    selected = select_nearest_html_capture(captures, year)
    if selected is None:
        return (
            HistoricalHomepageFetch(
                capture=None,
                replay_url="",
                html="",
                error="no_eligible_homepage_capture",
            ),
            query_metadata,
        )
    replay_url = build_replay_url(
        selected.timestamp.strftime("%Y%m%d%H%M%S"), selected.original_url
    )
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(replay_url)
            response.raise_for_status()
        return (
            HistoricalHomepageFetch(capture=selected, replay_url=replay_url, html=response.text),
            query_metadata,
        )
    except Exception as exc:  # Fetch failures are audited, not fatal to the whole run.
        return (
            HistoricalHomepageFetch(
                capture=selected,
                replay_url=replay_url,
                html="",
                error=f"{type(exc).__name__}: {exc}",
            ),
            query_metadata,
        )


def query_domain_identity_captures(
    domain: str,
    year: int,
    *,
    timeout_seconds: float = 15.0,
    limit: int = DOMAIN_DISCOVERY_LIMIT,
) -> tuple[list[CdxCapture], dict[str, Any]]:
    """Query Wayback CDX broadly for historical identity/value URLs on a domain."""
    params: list[tuple[str, str]] = [
        ("url", domain),
        ("matchType", "domain"),
        ("from", str(year)),
        ("to", str(year)),
        ("output", "json"),
        ("fl", ",".join(CDX_FIELDS)),
        ("filter", "statuscode:200"),
        ("filter", "mimetype:text/html"),
        ("collapse", "urlkey"),
        ("limit", str(limit)),
    ]
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = client.get(CDX_ENDPOINT, params=params)
        response.raise_for_status()
        payload = response.json()
    captures = parse_cdx_rows(payload)
    return captures, {
        "endpoint": CDX_ENDPOINT,
        "params": dict(params),
        "requested_at": datetime.now(UTC).isoformat(),
        "response_status": response.status_code,
        "capture_count": len(captures),
    }


def select_domain_discovered_urls(
    captures: list[CdxCapture],
    *,
    max_candidates: int = DOMAIN_DISCOVERY_MAX_CANDIDATES,
) -> list[str]:
    """Pick a small, auditable set of likely identity/value URLs from domain CDX rows."""
    best_by_url: dict[str, tuple[int, str]] = {}
    for capture in captures:
        normalized = normalize_url(capture.original_url)
        score = discovered_url_score(normalized)
        if score <= 0:
            continue
        current = best_by_url.get(normalized)
        if current is None or score > current[0]:
            best_by_url[normalized] = (score, capture.original_url)
    ranked = sorted(
        best_by_url.values(),
        key=lambda item: (-item[0], len(urlsplit(item[1]).path), item[1]),
    )
    return [url for _score, url in ranked[:max_candidates]]


def keep_existing_generated_candidate(
    row: dict[str, str],
    *,
    enable_domain_cdx_discovery: bool,
) -> bool:
    """Keep historical candidates that are enabled for the current reproducible run."""
    if row.get("discovery_method") == "historical_url_variant":
        return False
    if row.get("discovery_method") == "historical_domain_cdx_url":
        return enable_domain_cdx_discovery
    return True


def write_dict_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_dict_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def merge_candidate_files(
    seed_path: Path, generated_path: Path, output_path: Path
) -> list[dict[str, Any]]:
    """Merge manual and generated page candidates without rewriting the manual seed file."""
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for path in [seed_path, generated_path]:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                if not row.get("ticker") or not row.get("candidate_url"):
                    continue
                key = (
                    row["ticker"].strip(),
                    normalize_url(row["candidate_url"]),
                    str(row.get("valid_from_year", "")),
                    str(row.get("valid_to_year", "")),
                )
                merged[key] = {field: row.get(field, "") for field in CANDIDATE_CSV_FIELDS}
    rows = [
        merged[key]
        for key in sorted(
            merged,
            key=lambda item: (item[0], int(item[2] or 0), int(item[3] or 0), item[1]),
        )
    ]
    write_dict_rows(output_path, rows, CANDIDATE_CSV_FIELDS)
    return rows


def discover_historical_page_candidates(
    companies_path: Path,
    existing_candidates_path: Path,
    candidate_output_path: Path = DEFAULT_HISTORICAL_CANDIDATES,
    audit_output_path: Path = DEFAULT_HISTORICAL_DISCOVERY_AUDIT,
    *,
    target_keys: set[tuple[str, int]],
    query: Callable[..., tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    timeout_seconds: float = 15.0,
    workers: int = 1,
    enable_homepage_link_discovery: bool = True,
    enable_domain_cdx_discovery: bool = False,
    require_url_variant_cdx_capture: bool = False,
    url_variant_probe_retries: int = 3,
    url_variant_probe_backoff_seconds: float = 2.0,
    url_variant_probe_sleep_seconds: float = 0.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Discover same-year identity/value URLs from archived homepages for failed rows.

    The function is resume-friendly: it loads prior generated candidates and audit
    rows, skips completed homepage/domain/variant probes, and rewrites the generated
    CSVs deterministically. That makes historical discovery repeatable while preserving
    evidence for every URL considered.
    """
    if workers < 1:
        raise ValueError("workers must be at least 1")
    existing_urls = {
        (candidate.ticker, candidate.normalized_url)
        for candidate in load_page_candidates(existing_candidates_path)
    }
    existing_candidates = load_page_candidates(existing_candidates_path)
    companies: dict[str, dict[str, Any]] = {}
    with companies_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            historical_domains = [
                item.strip() for item in row["known_historical_domains"].split(";") if item.strip()
            ]
            domains = [row["primary_domain"], *historical_domains]
            companies[row["ticker"]] = {"domains": domains}

    generated_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in read_dict_rows(candidate_output_path):
        # Previously generated candidates are carried forward unless the current run
        # explicitly disables the discovery source that created them.
        if not keep_existing_generated_candidate(
            row,
            enable_domain_cdx_discovery=enable_domain_cdx_discovery,
        ):
            continue
        if row.get("ticker") and row.get("candidate_url") and row.get("valid_from_year"):
            key = (
                row["ticker"],
                normalize_url(row["candidate_url"]),
                int(row["valid_from_year"]),
            )
            generated_by_key[key] = {field: row.get(field, "") for field in CANDIDATE_CSV_FIELDS}

    audit_rows: list[dict[str, Any]] = read_dict_rows(audit_output_path)
    completed_homepages = {
        (row["ticker"], int(row["year"]), row["homepage_url"])
        for row in audit_rows
        if row.get("ticker") and row.get("year") and row.get("homepage_url")
    }
    completed_domain_queries = {
        (row["ticker"], int(row["year"]), row["domain"])
        for row in audit_rows
        if row.get("discovery_source") == "domain_cdx"
        and row.get("ticker")
        and row.get("year")
        and row.get("domain")
    }
    completed_variant_probes = {
        (row["ticker"], int(row["year"]), normalize_url(row["query_url"])): row
        for row in audit_rows
        if row.get("discovery_source") == "url_variant_cdx_probe"
        and row.get("ticker")
        and row.get("year")
        and row.get("query_url")
        and row.get("query_status")
        and row.get("query_status") != "failed"
        and not row.get("error")
    }

    for ticker, year in sorted(target_keys, key=lambda item: (item[0], item[1])):
        relevant_candidates = [
            candidate
            for candidate in existing_candidates
            if candidate.ticker == ticker
            and candidate.valid_from_year <= year <= candidate.valid_to_year
            and is_eligible_candidate(candidate)
        ]
        for candidate in relevant_candidates:
            for variant in select_url_variant_candidates(
                candidate.candidate_url,
                limit=URL_VARIANT_DISCOVERY_MAX_CANDIDATES,
            ):
                normalized = normalize_url(variant)
                if (ticker, normalized) in existing_urls:
                    continue
                if require_url_variant_cdx_capture:
                    # Optional precision gate: only add a generated variant when CDX
                    # confirms a same-year HTML capture for that exact URL.
                    cached_probe = completed_variant_probes.get((ticker, year, normalized))
                    if cached_probe is not None:
                        selected = (
                            CdxCapture(
                                timestamp=datetime.strptime(
                                    cached_probe["selected_capture_timestamp"], "%Y%m%d%H%M%S"
                                ).replace(tzinfo=UTC),
                                original_url=cached_probe["selected_original_url"],
                                status_code=200,
                                mime_type="text/html",
                            )
                            if cached_probe.get("selected_capture_timestamp")
                            and cached_probe.get("selected_original_url")
                            else None
                        )
                        if progress_callback:
                            progress_callback(
                                {
                                    "stage": "historical_url_discovery",
                                    "ticker": ticker,
                                    "year": year,
                                    "homepage_url": "",
                                    "status": "variant_probe_cached",
                                    "candidate_url": variant,
                                    "capture_count": cached_probe.get("capture_count", ""),
                                    "timestamp": datetime.now(UTC).isoformat(),
                                }
                            )
                        if selected is None:
                            continue
                    else:
                        captures, selected, metadata, error = probe_url_variant_capture(
                            variant,
                            year,
                            query=query,
                            timeout_seconds=timeout_seconds,
                            retries=url_variant_probe_retries,
                            backoff_seconds=url_variant_probe_backoff_seconds,
                            sleep_seconds=url_variant_probe_sleep_seconds,
                        )
                        audit_rows.append(
                            {
                                "discovery_source": "url_variant_cdx_probe",
                                "ticker": ticker,
                                "year": year,
                                "domain": urlsplit(normalized).hostname or "",
                                "query_url": variant,
                                "homepage_url": "",
                                "query_status": metadata.get("response_status", ""),
                                "capture_count": len(captures),
                                "selected_capture_timestamp": (
                                    selected.timestamp.strftime("%Y%m%d%H%M%S") if selected else ""
                                ),
                                "selected_original_url": selected.original_url if selected else "",
                                "selected_replay_url": (
                                    build_replay_url(
                                        selected.timestamp.strftime("%Y%m%d%H%M%S"),
                                        selected.original_url,
                                    )
                                    if selected
                                    else ""
                                ),
                                "fetched": False,
                                "discovered_link_count": 0,
                                "candidate_urls": json.dumps([variant] if selected else []),
                                "error": error,
                            }
                        )
                        if progress_callback:
                            progress_callback(
                                {
                                    "stage": "historical_url_discovery",
                                    "ticker": ticker,
                                    "year": year,
                                    "homepage_url": "",
                                    "status": (
                                        "variant_probe_failed"
                                        if metadata.get("response_status") == "failed"
                                        else "variant_probe"
                                    ),
                                    "candidate_url": variant,
                                    "capture_count": len(captures),
                                    "attempt_count": metadata.get("attempt_count", ""),
                                    "error": error,
                                    "timestamp": datetime.now(UTC).isoformat(),
                                }
                            )
                        if selected is None:
                            continue
                key = (ticker, normalized, year)
                generated_by_key[key] = {
                    "ticker": ticker,
                    "candidate_url": variant,
                    "page_type": page_type_from_discovered_url(variant),
                    "valid_from_year": year,
                    "valid_to_year": year,
                    "discovery_method": "historical_url_variant",
                    "eligibility_status": "eligible",
                    "eligibility_reason": (
                        "Conservative machine-generated variant of an approved candidate URL; "
                        "validated through same-year CDX and extraction gates."
                    ),
                    "reviewer": "pipeline_historical_discovery",
                }

    homepage_tasks: list[tuple[str, int, str, str]] = []
    domain_tasks: list[tuple[str, int, str]] = []
    for ticker, year in sorted(target_keys, key=lambda item: (item[0], item[1])):
        company = companies.get(ticker)
        if not company:
            continue
        for domain in company["domains"]:
            if (
                enable_domain_cdx_discovery
                and (ticker, year, domain) not in completed_domain_queries
            ):
                domain_tasks.append((ticker, year, domain))
            if not enable_homepage_link_discovery:
                continue
            for homepage_url in homepage_variants_for_domain(domain):
                homepage_key = (ticker, year, homepage_url)
                if homepage_key in completed_homepages:
                    if progress_callback:
                        progress_callback(
                            {
                                "stage": "historical_url_discovery",
                                "ticker": ticker,
                                "year": year,
                                "homepage_url": homepage_url,
                                "status": "cached",
                                "discovered_link_count": "",
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        )
                    continue
                homepage_tasks.append((ticker, year, domain, homepage_url))

    def discover_one(task: tuple[str, int, str, str]) -> tuple[dict[str, Any], list[str]]:
        ticker, year, domain, homepage_url = task
        try:
            fetch, metadata = fetch_homepage_capture(
                homepage_url,
                year,
                query=query,
                timeout_seconds=timeout_seconds,
            )
            links = (
                discover_candidate_links_from_homepage(fetch.html, homepage_url)
                if fetch.html
                else []
            )
            selected_timestamp = (
                fetch.capture.timestamp.strftime("%Y%m%d%H%M%S") if fetch.capture else ""
            )
            selected_original_url = fetch.capture.original_url if fetch.capture else ""
            return (
                {
                    "ticker": ticker,
                    "year": year,
                    "domain": domain,
                    "discovery_source": "homepage_link",
                    "query_url": "",
                    "homepage_url": homepage_url,
                    "query_status": metadata.get("response_status", ""),
                    "capture_count": metadata.get("capture_count", 0),
                    "selected_capture_timestamp": selected_timestamp,
                    "selected_original_url": selected_original_url,
                    "selected_replay_url": fetch.replay_url,
                    "fetched": bool(fetch.html),
                    "discovered_link_count": len(links),
                    "candidate_urls": json.dumps(links),
                    "error": fetch.error,
                },
                links,
            )
        except Exception as exc:
            return (
                {
                    "ticker": ticker,
                    "year": year,
                    "domain": domain,
                    "discovery_source": "homepage_link",
                    "query_url": "",
                    "homepage_url": homepage_url,
                    "query_status": "failed",
                    "capture_count": 0,
                    "selected_capture_timestamp": "",
                    "selected_original_url": "",
                    "selected_replay_url": "",
                    "fetched": False,
                    "discovered_link_count": 0,
                    "candidate_urls": "[]",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                [],
            )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(discover_one, task): task for task in homepage_tasks}
        for future in as_completed(futures):
            ticker, year, _domain, homepage_url = futures[future]
            audit_row, links = future.result()
            audit_rows.append(audit_row)
            completed_homepages.add((ticker, year, homepage_url))
            for link in links:
                normalized = normalize_url(link)
                if (ticker, normalized) in existing_urls:
                    continue
                key = (ticker, normalized, year)
                generated_by_key[key] = {
                    "ticker": ticker,
                    "candidate_url": link,
                    "page_type": page_type_from_discovered_url(link),
                    "valid_from_year": year,
                    "valid_to_year": year,
                    "discovery_method": "historical_homepage_link",
                    "eligibility_status": "eligible",
                    "eligibility_reason": (
                        "Machine-discovered from same-year archived homepage link; "
                        "audit before substantive interpretation."
                    ),
                    "reviewer": "pipeline_historical_discovery",
                }
            generated_rows = [
                generated_by_key[key]
                for key in sorted(generated_by_key, key=lambda item: (item[0], item[2], item[1]))
            ]
            write_dict_rows(candidate_output_path, generated_rows, CANDIDATE_CSV_FIELDS)
            write_dict_rows(
                audit_output_path,
                audit_rows,
                HISTORICAL_DISCOVERY_AUDIT_FIELDS,
            )
            if progress_callback:
                progress_callback(
                    {
                        "stage": "historical_url_discovery",
                        "ticker": ticker,
                        "year": year,
                        "homepage_url": homepage_url,
                        "status": "completed",
                        "discovered_link_count": audit_row.get("discovered_link_count", ""),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

    def discover_domain_one(task: tuple[str, int, str]) -> tuple[dict[str, Any], list[str]]:
        ticker, year, domain = task
        try:
            captures, metadata = query_domain_identity_captures(
                domain,
                year,
                timeout_seconds=timeout_seconds,
            )
            urls = select_domain_discovered_urls(captures)
            query_url = str(metadata.get("endpoint", ""))
            return (
                {
                    "discovery_source": "domain_cdx",
                    "ticker": ticker,
                    "year": year,
                    "domain": domain,
                    "query_url": query_url,
                    "homepage_url": "",
                    "query_status": metadata.get("response_status", ""),
                    "capture_count": metadata.get("capture_count", 0),
                    "selected_capture_timestamp": "",
                    "selected_original_url": "",
                    "selected_replay_url": "",
                    "fetched": False,
                    "discovered_link_count": len(urls),
                    "candidate_urls": json.dumps(urls),
                    "error": "",
                },
                urls,
            )
        except Exception as exc:
            return (
                {
                    "discovery_source": "domain_cdx",
                    "ticker": ticker,
                    "year": year,
                    "domain": domain,
                    "query_url": CDX_ENDPOINT,
                    "homepage_url": "",
                    "query_status": "failed",
                    "capture_count": 0,
                    "selected_capture_timestamp": "",
                    "selected_original_url": "",
                    "selected_replay_url": "",
                    "fetched": False,
                    "discovered_link_count": 0,
                    "candidate_urls": "[]",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                [],
            )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(discover_domain_one, task): task for task in domain_tasks}
        for future in as_completed(futures):
            ticker, year, domain = futures[future]
            audit_row, urls = future.result()
            audit_rows.append(audit_row)
            completed_domain_queries.add((ticker, year, domain))
            for url in urls:
                normalized = normalize_url(url)
                if (ticker, normalized) in existing_urls:
                    continue
                key = (ticker, normalized, year)
                generated_by_key[key] = {
                    "ticker": ticker,
                    "candidate_url": url,
                    "page_type": page_type_from_discovered_url(url),
                    "valid_from_year": year,
                    "valid_to_year": year,
                    "discovery_method": "historical_domain_cdx_url",
                    "eligibility_status": "eligible",
                    "eligibility_reason": (
                        "Machine-discovered from same-year domain-level CDX index; "
                        "audit before substantive interpretation."
                    ),
                    "reviewer": "pipeline_historical_discovery",
                }
            generated_rows = [
                generated_by_key[key]
                for key in sorted(generated_by_key, key=lambda item: (item[0], item[2], item[1]))
            ]
            write_dict_rows(candidate_output_path, generated_rows, CANDIDATE_CSV_FIELDS)
            write_dict_rows(
                audit_output_path,
                audit_rows,
                HISTORICAL_DISCOVERY_AUDIT_FIELDS,
            )
            if progress_callback:
                progress_callback(
                    {
                        "stage": "historical_url_discovery",
                        "ticker": ticker,
                        "year": year,
                        "domain": domain,
                        "status": "completed",
                        "discovery_source": "domain_cdx",
                        "discovered_link_count": audit_row.get("discovered_link_count", ""),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

    generated_rows = [
        generated_by_key[key]
        for key in sorted(generated_by_key, key=lambda item: (item[0], item[2], item[1]))
    ]
    write_dict_rows(candidate_output_path, generated_rows, CANDIDATE_CSV_FIELDS)
    write_dict_rows(audit_output_path, audit_rows, HISTORICAL_DISCOVERY_AUDIT_FIELDS)
    return generated_rows, audit_rows


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


def candidate_cache_path(
    cache_dir: Path, candidate: PageCandidate, year: int | None = None
) -> Path:
    identity = f"{candidate.ticker}\n{candidate.normalized_url}".encode()
    digest = hashlib.sha256(identity).hexdigest()[:16]
    suffix = f"-{year}" if year is not None else ""
    return cache_dir / f"{candidate.ticker.lower()}-{digest}{suffix}.json"


def _capture_payload(capture: CdxCapture) -> dict[str, Any]:
    payload = capture.model_dump(mode="json")
    payload["replay_url"] = build_replay_url(
        capture.timestamp.strftime("%Y%m%d%H%M%S"), capture.original_url
    )
    return payload


def collect_candidate_year(
    candidate: PageCandidate,
    year: int,
    cache_dir: Path,
    *,
    query: Callable[..., tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    retries: int = 5,
    backoff_seconds: float = 1.0,
    timeout_seconds: float = 90.0,
    prefix_fallback: bool = True,
    availability_fallback: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
    force: bool = False,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Collect one candidate-year, reusing only completed successful cache records."""
    if retries < 1:
        raise ValueError("retries must be at least 1")
    cache_path = candidate_cache_path(cache_dir, candidate, year)
    fallback_cached_record: dict[str, Any] | None = None
    if cache_path.exists() and not force:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("collection_status") == "success":
            captures = cached.get("captures", [])
            needs_availability_retry = (
                availability_fallback
                and not captures
                and cached.get("query_strategy") != "availability_fallback"
            )
            if not needs_availability_retry:
                if progress_callback:
                    progress_callback(
                        {
                            "stage": "cdx_discovery",
                            "ticker": candidate.ticker,
                            "year": year,
                            "candidate_url": candidate.candidate_url,
                            "status": "cached",
                            "capture_count": len(captures),
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                    )
                return cached
            fallback_cached_record = cached

    error_messages: list[str] = []
    record: dict[str, Any] | None = None
    for attempt in range(1, retries + 1):
        try:
            captures, query_metadata = query(
                candidate.candidate_url,
                start_year=year,
                end_year=year,
                timeout_seconds=timeout_seconds,
            )
            strategy = "exact"
            if prefix_fallback and not captures:
                try:
                    captures, query_metadata = query(
                        candidate.candidate_url,
                        start_year=year,
                        end_year=year,
                        timeout_seconds=timeout_seconds,
                        match_type="prefix",
                    )
                    strategy = "prefix_fallback"
                except Exception as exc:
                    # Prefix CDX is a recovery probe. If exact CDX already returned a
                    # valid zero-capture response, keep that as completed evidence
                    # instead of turning the whole candidate-year into a failed query.
                    error_messages.append(f"prefix_fallback_{type(exc).__name__}: {exc}")
                    strategy = "exact_prefix_failed"
            if availability_fallback and not captures:
                capture, availability_metadata = query_wayback_available(
                    candidate.candidate_url,
                    target_year=year,
                    timeout_seconds=timeout_seconds,
                )
                query_metadata = availability_metadata
                if capture is not None:
                    captures = [capture]
                    strategy = "availability_fallback"
            record = {
                "ticker": candidate.ticker,
                "candidate_url": candidate.candidate_url,
                "normalized_url": candidate.normalized_url,
                "page_type": candidate.page_type,
                "valid_from_year": candidate.valid_from_year,
                "valid_to_year": candidate.valid_to_year,
                "eligibility_status": candidate.eligibility_status,
                "year": year,
                "collection_status": "success",
                "attempt_count": attempt,
                "query_strategy": strategy,
                "query": query_metadata,
                "captures": [_capture_payload(capture) for capture in captures],
            }
            if error_messages:
                record["errors"] = error_messages
            break
        except Exception as exc:  # Network clients expose several retryable exception types.
            error_messages.append(f"{type(exc).__name__}: {exc}")
            if attempt < retries:
                sleep(backoff_seconds * (2 ** (attempt - 1)) + jitter())
    else:
        if availability_fallback:
            try:
                capture, availability_metadata = query_wayback_available(
                    candidate.candidate_url,
                    target_year=year,
                    timeout_seconds=timeout_seconds,
                )
                if capture is not None:
                    record = {
                        "ticker": candidate.ticker,
                        "candidate_url": candidate.candidate_url,
                        "normalized_url": candidate.normalized_url,
                        "page_type": candidate.page_type,
                        "valid_from_year": candidate.valid_from_year,
                        "valid_to_year": candidate.valid_to_year,
                        "eligibility_status": candidate.eligibility_status,
                        "year": year,
                        "collection_status": "success",
                        "attempt_count": retries,
                        "query_strategy": "availability_fallback_after_cdx_error",
                        "query": availability_metadata,
                        "errors": error_messages,
                        "captures": [_capture_payload(capture)],
                    }
            except Exception as exc:
                error_messages.append(f"{type(exc).__name__}: {exc}")
        if record is None and fallback_cached_record is not None:
            record = fallback_cached_record
        if record is None:
            record = {
                "ticker": candidate.ticker,
                "candidate_url": candidate.candidate_url,
                "normalized_url": candidate.normalized_url,
                "page_type": candidate.page_type,
                "valid_from_year": candidate.valid_from_year,
                "valid_to_year": candidate.valid_to_year,
                "eligibility_status": candidate.eligibility_status,
                "year": year,
                "collection_status": "failed",
                "attempt_count": retries,
                "errors": error_messages,
                "captures": [],
            }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    if progress_callback:
        progress_callback(
            {
                "stage": "cdx_discovery",
                "ticker": candidate.ticker,
                "year": year,
                "candidate_url": candidate.candidate_url,
                "status": record["collection_status"],
                "query_strategy": record.get("query_strategy", ""),
                "attempt_count": record.get("attempt_count", ""),
                "capture_count": len(record.get("captures", [])),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
    return record


def collect_candidate(
    candidate: PageCandidate,
    cache_dir: Path,
    *,
    query: Callable[..., tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    retries: int = 5,
    backoff_seconds: float = 1.0,
    timeout_seconds: float = 90.0,
    prefix_fallback: bool = True,
    availability_fallback: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
    force: bool = False,
    target_years: set[int] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Collect all valid years for one candidate with per-year retry isolation."""
    years = [
        year
        for year in range(candidate.valid_from_year, candidate.valid_to_year + 1)
        if target_years is None or year in target_years
    ]
    year_records = [
        collect_candidate_year(
            candidate,
            year,
            cache_dir,
            query=query,
            retries=retries,
            backoff_seconds=backoff_seconds,
            timeout_seconds=timeout_seconds,
            prefix_fallback=prefix_fallback,
            availability_fallback=availability_fallback,
            sleep=sleep,
            jitter=jitter,
            force=force,
            progress_callback=progress_callback,
        )
        for year in years
    ]
    successful = [record for record in year_records if record["collection_status"] == "success"]
    if len(successful) == len(year_records):
        status = "success"
    elif successful:
        status = "partial"
    else:
        status = "failed"
    record = {
        "ticker": candidate.ticker,
        "candidate_url": candidate.candidate_url,
        "normalized_url": candidate.normalized_url,
        "page_type": candidate.page_type,
        "valid_from_year": candidate.valid_from_year,
        "valid_to_year": candidate.valid_to_year,
        "eligibility_status": candidate.eligibility_status,
        "collection_status": status,
        "attempt_count": sum(int(item.get("attempt_count", 0)) for item in year_records),
        "year_records": year_records,
        "captures": [
            capture for year_record in successful for capture in year_record.get("captures", [])
        ],
    }
    aggregate_path = candidate_cache_path(cache_dir, candidate)
    aggregate_path.parent.mkdir(parents=True, exist_ok=True)
    aggregate_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def query_log_rows(records: list[dict[str, Any]], cache_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        candidate = PageCandidate(
            ticker=record["ticker"],
            candidate_url=record["candidate_url"],
            normalized_url=record["normalized_url"],
            page_type=record["page_type"],
            valid_from_year=int(record["valid_from_year"]),
            valid_to_year=int(record["valid_to_year"]),
            eligibility_status=record["eligibility_status"],
        )
        for year_record in record.get("year_records", []):
            errors = year_record.get("errors", [])
            error_types = sorted({error.split(":", 1)[0] for error in errors})
            rows.append(
                {
                    "ticker": year_record["ticker"],
                    "candidate_url": year_record["candidate_url"],
                    "normalized_url": year_record["normalized_url"],
                    "year": year_record["year"],
                    "query_status": year_record["collection_status"],
                    "attempt_count": year_record.get("attempt_count", ""),
                    "capture_count": len(year_record.get("captures", [])),
                    "response_status": year_record.get("query", {}).get("response_status", ""),
                    "query_strategy": year_record.get("query_strategy", ""),
                    "requested_at": year_record.get("query", {}).get("requested_at", ""),
                    "error_types": ";".join(error_types),
                    "cache_path": str(
                        candidate_cache_path(cache_dir, candidate, year_record["year"])
                    ),
                }
            )
    return sorted(rows, key=lambda row: (row["ticker"], int(row["year"]), row["candidate_url"]))


def write_query_log(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=QUERY_LOG_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def discover_candidates(
    candidates_path: Path,
    cache_dir: Path,
    *,
    query: Callable[..., tuple[list[CdxCapture], dict[str, Any]]] = query_cdx,
    retries: int = 5,
    backoff_seconds: float = 1.0,
    timeout_seconds: float = 90.0,
    prefix_fallback: bool = True,
    availability_fallback: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
    force: bool = False,
    ticker: str | None = None,
    target_keys: set[tuple[str, int]] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    records = []
    for candidate in load_page_candidates(candidates_path):
        if ticker and candidate.ticker != ticker:
            continue
        target_years = None
        if target_keys is not None:
            target_years = {
                year for key_ticker, year in target_keys if key_ticker == candidate.ticker
            }
            if not target_years:
                continue
        if is_eligible_candidate(candidate):
            records.append(
                collect_candidate(
                    candidate,
                    cache_dir,
                    query=query,
                    retries=retries,
                    backoff_seconds=backoff_seconds,
                    timeout_seconds=timeout_seconds,
                    prefix_fallback=prefix_fallback,
                    availability_fallback=availability_fallback,
                    sleep=sleep,
                    jitter=jitter,
                    force=force,
                    target_years=target_years,
                    progress_callback=progress_callback,
                )
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_PAGE_CANDIDATES)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--query-log", type=Path, default=DEFAULT_QUERY_LOG)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--ticker")
    parser.add_argument("--no-prefix-fallback", action="store_true")
    parser.add_argument("--availability-fallback", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    records = discover_candidates(
        args.candidates,
        args.cache_dir,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
        timeout_seconds=args.timeout_seconds,
        prefix_fallback=not args.no_prefix_fallback,
        availability_fallback=args.availability_fallback,
        force=args.force,
        ticker=args.ticker,
    )
    write_query_log(query_log_rows(records, args.cache_dir), args.query_log)
    succeeded = sum(record["collection_status"] == "success" for record in records)
    partial = sum(record["collection_status"] == "partial" for record in records)
    print(f"Collected {succeeded}/{len(records)} eligible page candidates ({partial} partial)")


if __name__ == "__main__":
    main()
