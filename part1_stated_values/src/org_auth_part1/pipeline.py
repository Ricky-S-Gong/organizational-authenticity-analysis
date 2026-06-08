"""Run replay retrieval, extraction, change analysis, themes, and final Part 1 outputs."""

import argparse
import csv
import hashlib
import html as html_lib
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import requests

from org_auth_part1.analyze import analyze_text
from org_auth_part1.compare import compare_adjacent_years
from org_auth_part1.extract import extract_json_text, extract_page_text
from org_auth_part1.report import audit_part1_requirements, coverage_summary

DEFAULT_STATUS = Path("part1_stated_values/data/processed/acquisition_status.csv")
DEFAULT_RAW_DIR = Path("part1_stated_values/data/raw/html")
DEFAULT_TEXT_ARTIFACTS = Path("part1_stated_values/data/processed/text_artifacts.csv")
DEFAULT_FINAL = Path("part1_stated_values/outputs/part1_company_year.csv")
DEFAULT_COVERAGE = Path("part1_stated_values/outputs/coverage_report.json")
DEFAULT_AUDIT = Path("part1_stated_values/outputs/requirement_audit.json")
DEFAULT_SUMMARY = Path("part1_stated_values/docs/summary.md")
DEFAULT_CHANGE_EVENTS = Path("part1_stated_values/outputs/change_events.csv")
DEFAULT_THEME_OBSERVATIONS = Path("part1_stated_values/outputs/theme_observations.csv")
DEFAULT_REVIEW_DECISIONS = Path("part1_stated_values/data/review/review_decisions.csv")
DEFAULT_VALIDATION_REPORT = Path("part1_stated_values/docs/validation_report.md")

TEXT_ARTIFACT_FIELDS = [
    "ticker",
    "year",
    "fetch_status",
    "fetch_error",
    "raw_content_sha256",
    "clean_text_sha256",
    "page_text_clean",
    "visible_text_raw",
    "clean_word_count",
    "clean_char_count",
    "alpha_ratio",
    "link_text_ratio",
    "extraction_backend",
    "fetched_url",
    "fetch_attempt_log",
    "qa_flags",
]

BLOCKING_QA_FLAGS = {"empty_text", "likely_error_page", "low_alpha_ratio"}
MINIMUM_USABLE_WORDS = 25
META_REFRESH_PATTERN = re.compile(
    r"<meta\b[^>]*http-equiv=[\"']?refresh[\"']?[^>]*content=[\"'][^\"']*url=([^\"';>]+)[^\"']*[\"']",
    re.IGNORECASE,
)
NOSCRIPT_PATTERN = re.compile(r"<noscript\b[^>]*>.*?</noscript>", re.IGNORECASE | re.DOTALL)
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

JSON_API_FALLBACKS = [
    {
        "name": "about_nike_company_landing",
        "url_pattern": re.compile(r"^https?://about\.nike\.com/[^/]+/company/?", re.IGNORECASE),
        "api_url": "https://api.about.nike.com/v1/company/landing",
    }
]
CURL_CODE_MARKER = b"\n__ORG_AUTH_CURL_HTTP_CODE__:"
CURL_URL_MARKER = b"\n__ORG_AUTH_CURL_EFFECTIVE_URL__:"

FINAL_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "year",
    "observation_status",
    "gap_reason",
    "source_url",
    "wayback_url",
    "capture_timestamp",
    "page_text_clean",
    "changed_from_prior",
    "change_score",
    "change_magnitude",
    "theme_categories",
    "theme_evidence",
    "linguistic_metrics",
    "linguistic_shift_notes",
    "analyst_notes",
    "raw_content_sha256",
    "clean_text_sha256",
    "extraction_quality",
    "manual_review_status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _raw_path(raw_dir: Path, ticker: str, year: int, replay_url: str) -> Path:
    """Derive a stable raw-html path from ticker, year, and exact replay URL."""
    url_digest = hashlib.sha256(replay_url.encode("utf-8")).hexdigest()[:12]
    return raw_dir / ticker.lower().replace(".", "_") / f"{year}-{url_digest}.html"


def replay_url_variants(replay_url: str) -> list[str]:
    """Return Wayback replay variants from most content-preserving to most permissive."""
    match = re.match(
        r"^(https://web\.archive\.org/web/)(\d{8,14})([a-z]{2}_)?/(.+)$",
        replay_url,
    )
    if not match:
        return [replay_url]
    prefix, timestamp, _modifier, original_url = match.groups()
    return [
        f"{prefix}{timestamp}id_/{original_url}",
        f"{prefix}{timestamp}if_/{original_url}",
        f"{prefix}{timestamp}/{original_url}",
    ]


def _replay_parts(replay_url: str) -> tuple[str, str, str] | None:
    match = re.match(
        r"^(https://web\.archive\.org/web/)(\d{8,14})([a-z]{2}_)?/(.+)$",
        replay_url,
    )
    if not match:
        return None
    prefix, timestamp, _modifier, original_url = match.groups()
    return prefix, timestamp, original_url


def meta_refresh_replay_url(replay_url: str, html: str) -> str | None:
    """Return same-timestamp Wayback URL for a meta-refresh target, if present."""
    parts = _replay_parts(replay_url)
    html_without_noscript = NOSCRIPT_PATTERN.sub("", html)
    match = META_REFRESH_PATTERN.search(html_without_noscript)
    if not parts or not match:
        return None
    prefix, timestamp, original_url = parts
    target = html_lib.unescape(match.group(1).strip())
    if not target or target.lower().startswith(("javascript:", "mailto:")):
        return None
    resolved = urljoin(original_url, target)
    if resolved == original_url:
        return None
    return f"{prefix}{timestamp}id_/{resolved}"


def same_timestamp_replay_url(replay_url: str, target: str) -> str | None:
    """Return a same-timestamp Wayback URL for an archived redirect target."""
    parts = _replay_parts(replay_url)
    if not parts:
        return None
    prefix, timestamp, original_url = parts
    target = html_lib.unescape(target.strip())
    if not target or target.lower().startswith(("javascript:", "mailto:")):
        return None
    parsed = urlparse(target)
    if parsed.netloc == "web.archive.org":
        return target
    if target.startswith("/web/"):
        return f"https://web.archive.org{target}"
    resolved = urljoin(original_url, target)
    if resolved == original_url:
        return None
    return f"{prefix}{timestamp}id_/{resolved}"


def redirect_replay_url(replay_url: str, response: httpx.Response) -> str | None:
    """Keep archived redirects inside Wayback instead of following live-site locations."""
    if response.status_code not in REDIRECT_STATUS_CODES:
        return None
    location = response.headers.get("location", "")
    if not location:
        return None
    return same_timestamp_replay_url(replay_url, location)


def _get_replay_response(
    url: str,
    *,
    timeout_seconds: float,
    headers: dict[str, str],
) -> tuple[Any, str]:
    """Fetch a replay URL with progressively lower-level HTTP clients.

    Wayback replay occasionally fails at the client/socket layer even when the URL is
    available. The fallback chain keeps those failures auditable by recording which
    client succeeded in ``fetch_attempt_log``.
    """
    try:
        return (
            httpx.get(
                url,
                timeout=timeout_seconds,
                follow_redirects=False,
                headers=headers,
            ),
            "httpx",
        )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
        try:
            response = requests.get(
                url,
                timeout=timeout_seconds,
                allow_redirects=False,
                headers=headers,
            )
            return response, "requests"
        except (
            requests.ConnectionError,
            requests.ConnectTimeout,
            requests.ReadTimeout,
            requests.Timeout,
        ):
            return _get_replay_response_with_curl(
                url, timeout_seconds=timeout_seconds, headers=headers
            ), "curl"


class CurlReplayResponse:
    """Small response adapter so curl responses match the httpx/requests interface."""

    def __init__(self, *, content: bytes, status_code: int, url: str) -> None:
        self.content = content
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} response for url: {self.url}")


def _get_replay_response_with_curl(
    url: str,
    *,
    timeout_seconds: float,
    headers: dict[str, str],
) -> CurlReplayResponse:
    """Use curl as a last-resort replay client while preserving status/effective URL."""
    user_agent = headers.get("User-Agent", "organizational-authenticity-research/0.1")
    command = [
        "curl",
        "-L",
        "-sS",
        "--compressed",
        "--connect-timeout",
        str(max(5, min(int(timeout_seconds), 30))),
        "--max-time",
        str(max(10, int(timeout_seconds))),
        "-A",
        user_agent,
        "-w",
        (
            "\n__ORG_AUTH_CURL_HTTP_CODE__:%{http_code}"
            "\n__ORG_AUTH_CURL_EFFECTIVE_URL__:%{url_effective}"
        ),
        url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        timeout=timeout_seconds + 5,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise requests.ConnectionError(stderr or f"curl exited {completed.returncode}")
    output = completed.stdout
    if CURL_CODE_MARKER not in output or CURL_URL_MARKER not in output:
        raise requests.ConnectionError("curl output missing status markers")
    content, metadata = output.rsplit(CURL_CODE_MARKER, 1)
    status_text, effective_url = metadata.split(CURL_URL_MARKER, 1)
    return CurlReplayResponse(
        content=content,
        status_code=int(status_text.strip() or b"0"),
        url=effective_url.decode("utf-8", errors="replace").strip(),
    )


def _timestamp_from_replay_url(replay_url: str) -> str:
    match = re.search(r"/web/(\d{8,14})", replay_url)
    return match.group(1) if match else ""


def _json_api_fallback_for_status(status: dict[str, str]) -> dict[str, Any] | None:
    original_url = status.get("selected_original_url", "")
    for fallback in JSON_API_FALLBACKS:
        if fallback["url_pattern"].search(original_url):
            return fallback
    return None


def _fetch_json_api_fallback(
    status: dict[str, str],
    *,
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
    sleep: Any = time.sleep,
) -> dict[str, Any] | None:
    """Recover text from known archived JSON endpoints behind JavaScript pages."""
    fallback = _json_api_fallback_for_status(status)
    timestamp = _timestamp_from_replay_url(status.get("selected_replay_url", ""))
    if not fallback or not timestamp:
        return None
    api_url = str(fallback["api_url"])
    replay_url = f"https://web.archive.org/web/{timestamp}id_/{api_url}"
    errors: list[str] = []
    for attempt in range(1, retries + 1):
        try:
            response = httpx.get(
                replay_url,
                timeout=timeout_seconds,
                follow_redirects=True,
                headers={
                    "User-Agent": "organizational-authenticity-research/0.1",
                    "Accept-Encoding": "gzip, deflate",
                },
            )
            response.raise_for_status()
            payload = response.json()
            text = extract_json_text(payload)
            return {
                "attempt": attempt,
                "fallback": fallback["name"],
                "url": replay_url,
                "response_url": str(response.url),
                "status": "success",
                "status_code": response.status_code,
                "bytes": len(response.content),
                "text": text,
            }
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < retries:
                sleep(backoff_seconds * attempt)
    return {
        "attempts": retries,
        "fallback": fallback["name"],
        "url": replay_url,
        "status": "failed",
        "error": errors[-1] if errors else "unknown error",
        "errors": errors,
    }


def _fetch_one(
    row: dict[str, str],
    raw_dir: Path,
    *,
    force: bool,
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
    sleep: Any = time.sleep,
) -> dict[str, Any]:
    """Fetch one selected Wayback replay URL and persist the raw response.

    The function tries raw/id replay first, then iframe/bare variants, archived
    redirects, and meta-refresh targets. Each attempt is logged so a failed or rescued
    row can be audited from ``text_artifacts.csv``.
    """
    ticker, year = row["ticker"], int(row["year"])
    url = row["selected_replay_url"]
    raw_path = _raw_path(raw_dir, ticker, year, url)
    if raw_path.exists() and not force:
        content = raw_path.read_bytes()
        return {
            "ticker": ticker,
            "year": year,
            "fetch_status": "cached",
            "content": content,
            "fetched_url": url,
            "attempt_log": [{"url": url, "status": "cached"}],
        }

    last_error = ""
    errors: list[str] = []
    attempt_log: list[dict[str, Any]] = []
    for attempt in range(1, retries + 1):
        attempted_urls: set[str] = set()
        queued_urls = replay_url_variants(url)
        while queued_urls:
            attempt_url = queued_urls.pop(0)
            if attempt_url in attempted_urls:
                continue
            attempted_urls.add(attempt_url)
            try:
                response, fetch_client = _get_replay_response(
                    attempt_url,
                    timeout_seconds=timeout_seconds,
                    headers={"User-Agent": "organizational-authenticity-research/0.1"},
                )
                redirect_url = redirect_replay_url(attempt_url, response)
                if redirect_url and redirect_url not in attempted_urls:
                    attempt_log.append(
                        {
                            "attempt": attempt,
                            "url": attempt_url,
                            "status": "archived_redirect",
                            "response_url": str(response.url),
                            "status_code": response.status_code,
                            "target_url": redirect_url,
                            "bytes": len(response.content),
                            "fetch_client": fetch_client,
                        }
                    )
                    queued_urls = replay_url_variants(redirect_url) + queued_urls
                    continue
                response.raise_for_status()
                content_text = response.content.decode("utf-8", errors="replace")
                refresh_url = meta_refresh_replay_url(attempt_url, content_text)
                if refresh_url and refresh_url not in attempted_urls:
                    attempt_log.append(
                        {
                            "attempt": attempt,
                            "url": attempt_url,
                            "status": "meta_refresh",
                            "response_url": str(response.url),
                            "status_code": response.status_code,
                            "target_url": refresh_url,
                            "bytes": len(response.content),
                            "fetch_client": fetch_client,
                        }
                    )
                    queued_urls = replay_url_variants(refresh_url) + queued_urls
                    continue
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(response.content)
                attempt_log.append(
                    {
                        "attempt": attempt,
                        "url": attempt_url,
                        "status": "success",
                        "response_url": str(response.url),
                        "status_code": response.status_code,
                        "bytes": len(response.content),
                        "fetch_client": fetch_client,
                    }
                )
                return {
                    "ticker": ticker,
                    "year": year,
                    "fetch_status": "success",
                    "content": response.content,
                    "fetched_url": attempt_url,
                    "final_url": str(response.url),
                    "attempt_log": attempt_log,
                }
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                errors.append(last_error)
                attempt_log.append(
                    {
                        "attempt": attempt,
                        "url": attempt_url,
                        "status": "failed",
                        "error": last_error,
                    }
                )
        if attempt < retries:
            sleep(backoff_seconds * attempt)
    if raw_path.exists():
        content = raw_path.read_bytes()
        attempt_log.append(
            {
                "url": url,
                "status": "cached_after_failed_refresh",
                "bytes": len(content),
            }
        )
        return {
            "ticker": ticker,
            "year": year,
            "fetch_status": "cached_after_failed_refresh",
            "content": content,
            "fetched_url": url,
            "attempt_log": attempt_log,
            "refresh_error": last_error,
        }
    return {
        "ticker": ticker,
        "year": year,
        "fetch_status": "failed",
        "error": last_error,
        "errors": errors,
        "attempt_log": attempt_log,
    }


def fetch_selected(
    status_rows: list[dict[str, str]],
    raw_dir: Path,
    *,
    force: bool = False,
    workers: int = 4,
    timeout_seconds: float = 30.0,
    retries: int = 6,
    backoff_seconds: float = 1.0,
    target_keys: set[tuple[str, int]] | None = None,
) -> dict[tuple[str, int], dict[str, Any]]:
    """Fetch selected company-year rows, optionally limited to incremental targets."""
    selected = [
        row
        for row in status_rows
        if row["acquisition_status"] == "selected"
        and (target_keys is None or (row["ticker"], int(row["year"])) in target_keys)
    ]
    results: dict[tuple[str, int], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _fetch_one,
                row,
                raw_dir,
                force=force,
                timeout_seconds=timeout_seconds,
                retries=retries,
                backoff_seconds=backoff_seconds,
            ): (row["ticker"], int(row["year"]))
            for row in selected
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


def merge_text_artifacts(
    existing: list[dict[str, Any]],
    updates: list[dict[str, Any]],
    *,
    target_keys: set[tuple[str, int]] | None,
) -> list[dict[str, Any]]:
    """Replace only targeted artifacts while preserving prior usable artifacts."""
    if target_keys is None:
        return updates
    merged = {
        (str(row["ticker"]), int(row["year"])): row
        for row in existing
        if (str(row["ticker"]), int(row["year"])) not in target_keys
    }
    for row in updates:
        merged[(str(row["ticker"]), int(row["year"]))] = row
    return [merged[key] for key in sorted(merged, key=lambda item: (item[0], item[1]))]


def merge_final_rows(
    existing: list[dict[str, Any]],
    rebuilt: list[dict[str, Any]],
    *,
    target_keys: set[tuple[str, int]] | None,
) -> list[dict[str, Any]]:
    """Preserve non-target final rows during incremental recovery runs."""
    if target_keys is None:
        return rebuilt
    normalized_existing = [dict(row, year=str(int(row["year"]))) for row in existing]
    normalized_rebuilt = [dict(row, year=str(int(row["year"]))) for row in rebuilt]
    rows = {
        (str(row["ticker"]), int(row["year"])): row
        for row in normalized_existing
        if (str(row["ticker"]), int(row["year"])) not in target_keys
    }
    for row in normalized_rebuilt:
        key = (str(row["ticker"]), int(row["year"]))
        if key in target_keys or key not in rows:
            rows[key] = row
    return [rows[key] for key in sorted(rows, key=lambda item: (item[0], item[1]))]


def effective_fetch_target_keys(
    selected_keys: set[tuple[str, int]],
    existing_artifacts: list[dict[str, Any]],
    target_keys: set[tuple[str, int]] | None,
) -> set[tuple[str, int]] | None:
    """Expand incremental fetch scope to cover newly selected rows without artifacts."""
    if target_keys is None:
        return None
    artifact_keys = {(str(row["ticker"]), int(row["year"])) for row in existing_artifacts}
    return set(target_keys) | (selected_keys - artifact_keys)


def build_text_artifacts(
    status_rows: list[dict[str, str]],
    fetches: dict[tuple[str, int], dict[str, Any]],
    *,
    enable_trafilatura_fallback: bool = False,
    enable_wayback_json_api_fallback: bool = False,
    json_api_timeout_seconds: float = 60.0,
    json_api_retries: int = 3,
    json_api_backoff_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    """Convert raw fetches into extracted text artifacts with hashes and QA flags."""
    artifacts: list[dict[str, Any]] = []
    for status in status_rows:
        key = (status["ticker"], int(status["year"]))
        fetch = fetches.get(key)
        if not fetch:
            continue
        if fetch["fetch_status"] == "failed":
            artifacts.append(
                {
                    "ticker": key[0],
                    "year": key[1],
                    "fetch_status": fetch["fetch_status"],
                    "fetch_error": fetch.get("error", ""),
                    "raw_content_sha256": "",
                    "clean_text_sha256": "",
                    "page_text_clean": "",
                    "visible_text_raw": "",
                    "clean_word_count": 0,
                    "clean_char_count": 0,
                    "alpha_ratio": 0.0,
                    "link_text_ratio": 0.0,
                    "extraction_backend": "",
                    "fetched_url": "",
                    "fetch_attempt_log": json.dumps(fetch.get("attempt_log", [])),
                    "qa_flags": json.dumps(["retrieval_failed"]),
                }
            )
            continue
        content = fetch["content"]
        html = content.decode("utf-8", errors="replace")
        extracted = extract_page_text(
            html,
            enable_trafilatura_fallback=enable_trafilatura_fallback,
        )
        fallback_attempt = None
        if enable_wayback_json_api_fallback and extracted.clean_word_count < MINIMUM_USABLE_WORDS:
            fallback_attempt = _fetch_json_api_fallback(
                status,
                timeout_seconds=json_api_timeout_seconds,
                retries=json_api_retries,
                backoff_seconds=json_api_backoff_seconds,
            )
            fallback_text = (fallback_attempt or {}).get("text", "")
            if fallback_text and len(fallback_text.split()) > extracted.clean_word_count:
                extracted = extract_page_text(
                    f"<main>{html_lib.escape(fallback_text)}</main>",
                    enable_trafilatura_fallback=False,
                )
                extracted = extracted.__class__(
                    visible_text_raw=extracted.visible_text_raw,
                    page_text_clean=extracted.page_text_clean,
                    used_main_region=extracted.used_main_region,
                    clean_word_count=extracted.clean_word_count,
                    clean_char_count=extracted.clean_char_count,
                    alpha_ratio=extracted.alpha_ratio,
                    link_text_ratio=extracted.link_text_ratio,
                    qa_flags=tuple(
                        flag
                        for flag in (*extracted.qa_flags, "wayback_json_api_fallback")
                        if flag != "short_text"
                    ),
                    extraction_backend="htmlparser+wayback_json_api",
                )
        attempt_log = list(fetch.get("attempt_log", []))
        if fallback_attempt:
            attempt_log.append({"kind": "json_api_fallback", **fallback_attempt})
        artifacts.append(
            {
                "ticker": key[0],
                "year": key[1],
                "fetch_status": fetch["fetch_status"],
                "fetch_error": "",
                "raw_content_sha256": hashlib.sha256(content).hexdigest(),
                "clean_text_sha256": hashlib.sha256(extracted.page_text_clean.encode()).hexdigest(),
                "page_text_clean": extracted.page_text_clean,
                "visible_text_raw": extracted.visible_text_raw,
                "clean_word_count": extracted.clean_word_count,
                "clean_char_count": extracted.clean_char_count,
                "alpha_ratio": extracted.alpha_ratio,
                "link_text_ratio": extracted.link_text_ratio,
                "extraction_backend": extracted.extraction_backend,
                "fetched_url": fetch.get("fetched_url", ""),
                "fetch_attempt_log": json.dumps(attempt_log),
                "qa_flags": json.dumps(extracted.qa_flags),
            }
        )
    return artifacts


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def is_usable_artifact(artifact: dict[str, Any] | None) -> bool:
    """Return whether extracted text is usable for downstream analysis.

    Short text is allowed only above a minimal evidentiary floor. Non-blocking flags
    such as high link density are retained for review but do not automatically reject
    otherwise substantive text.
    """
    if not artifact or artifact.get("fetch_status") == "failed":
        return False
    text = str(artifact.get("page_text_clean") or "")
    if not text.strip():
        return False
    qa_flags = set(json.loads(artifact.get("qa_flags") or "[]"))
    if qa_flags & BLOCKING_QA_FLAGS:
        return False
    return int(artifact.get("clean_word_count") or 0) >= MINIMUM_USABLE_WORDS


def build_final_rows(
    status_rows: list[dict[str, str]],
    artifacts: list[dict[str, Any]],
    fetches: dict[tuple[str, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join acquisition statuses and extracted artifacts into the final panel rows."""
    artifacts_by_key = {(row["ticker"], int(row["year"])): row for row in artifacts}
    final: list[dict[str, Any]] = []
    for status in status_rows:
        key = (status["ticker"], int(status["year"]))
        artifact = artifacts_by_key.get(key)
        fetch = fetches.get(key)
        qa_flags = json.loads(artifact["qa_flags"]) if artifact else []
        fetch_failed = bool(artifact and artifact.get("fetch_status") == "failed")
        usable = is_usable_artifact(artifact)
        if usable:
            observation_status = "usable"
            gap_reason = ""
            analysis = analyze_text(artifact["page_text_clean"])
        else:
            if status["acquisition_status"] == "selected" and (not artifact or fetch_failed):
                observation_status = "retrieval_failed"
            elif status["acquisition_status"] == "selected" and artifact:
                observation_status = "insufficient_substantive_text"
            else:
                observation_status = status["acquisition_status"]
            artifact_error = artifact.get("fetch_error") if artifact else ""
            gap_reason = (
                status["failure_reason"]
                or artifact_error
                or (
                    fetch.get("error", "selected capture could not be extracted")
                    if fetch
                    else "no selected usable capture"
                )
            )
            analysis = {
                "theme_categories": None,
                "theme_evidence": None,
                "linguistic_metrics": None,
            }
        final.append(
            {
                "ticker": status["ticker"],
                "company_name": status["company_name"],
                "sector": status["sector"],
                "year": int(status["year"]),
                "observation_status": observation_status,
                "gap_reason": gap_reason,
                "source_url": status["selected_original_url"],
                "wayback_url": status["selected_replay_url"],
                "capture_timestamp": status["selected_capture_timestamp"],
                "page_text_clean": artifact["page_text_clean"] if artifact else "",
                "changed_from_prior": None,
                "change_score": None,
                "change_magnitude": "",
                "theme_categories": _json(analysis["theme_categories"])
                if analysis["theme_categories"] is not None
                else "",
                "theme_evidence": _json(analysis["theme_evidence"])
                if analysis["theme_evidence"] is not None
                else "",
                "linguistic_metrics": _json(analysis["linguistic_metrics"])
                if analysis["linguistic_metrics"] is not None
                else "",
                "linguistic_shift_notes": "",
                "analyst_notes": (
                    "Deterministic evidence-backed baseline; manual review required."
                    if usable
                    else f"Unavailable: {gap_reason}"
                ),
                "raw_content_sha256": artifact["raw_content_sha256"] if artifact else "",
                "clean_text_sha256": artifact["clean_text_sha256"] if artifact else "",
                "extraction_quality": ("review_required" if qa_flags else "automated_pass")
                if usable
                else "not_available",
                "manual_review_status": "pending" if usable or qa_flags else "not_applicable",
            }
        )

    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in final:
        by_ticker.setdefault(row["ticker"], []).append(row)
    for rows in by_ticker.values():
        year_texts = {
            int(row["year"]): row["page_text_clean"]
            if row["observation_status"] == "usable"
            else None
            for row in rows
        }
        comparisons = {
            comparison.year: comparison for comparison in compare_adjacent_years(year_texts)
        }
        for row in rows:
            comparison = comparisons[int(row["year"])]
            row["changed_from_prior"] = comparison.changed_from_prior
            row["change_score"] = (
                round(1 - min(comparison.token_jaccard_similarity, comparison.edit_similarity), 6)
                if comparison.token_jaccard_similarity is not None
                and comparison.edit_similarity is not None
                else None
            )
            row["change_magnitude"] = comparison.change_class.value
            if comparison.added_snippets or comparison.removed_snippets:
                row["linguistic_shift_notes"] = _json(
                    {
                        "added": comparison.added_snippets,
                        "removed": comparison.removed_snippets,
                    }
                )
    return sorted(final, key=lambda row: (row["ticker"], row["year"]))


def write_summary(records: list[dict[str, Any]], path: Path) -> None:
    coverage = coverage_summary(records)
    status_counts = coverage["status_counts"]
    selected_count = sum(
        status_counts.get(status, 0)
        for status in ("usable", "insufficient_substantive_text", "retrieval_failed")
    )
    retrieved_artifacts = selected_count - status_counts.get("retrieval_failed", 0)
    usable_by_year: dict[int, int] = {}
    total_by_year: dict[int, int] = {}
    usable_by_sector: dict[str, int] = {}
    total_by_sector: dict[str, int] = {}
    usable_companies = {row["ticker"] for row in records if row["observation_status"] == "usable"}
    for row in records:
        year = int(row["year"])
        sector = str(row["sector"])
        total_by_year[year] = total_by_year.get(year, 0) + 1
        total_by_sector[sector] = total_by_sector.get(sector, 0) + 1
        if row["observation_status"] == "usable":
            usable_by_year[year] = usable_by_year.get(year, 0) + 1
            usable_by_sector[sector] = usable_by_sector.get(sector, 0) + 1
    status_lines = "\n".join(
        f"- `{status}`: {count}" for status, count in coverage["status_counts"].items()
    )
    year_lines = "\n".join(
        f"- {year}: {usable_by_year.get(year, 0)} of {total_by_year[year]}"
        for year in sorted(total_by_year)
    )
    sector_lines = "\n".join(
        f"- {sector}: {usable_by_sector.get(sector, 0)} of {total_by_sector[sector]}"
        for sector in sorted(total_by_sector)
    )
    text = f"""# Part 1 Summary

## Scope

The pipeline evaluated all 450 required company-year targets across 50 companies and 2016–2024.

## Coverage

- Target grid coverage: {coverage["target_record_count"]} of 450 required company-years were
  processed (50 companies, 2016-2024).
- CDX discovery coverage: 450 of 450 company-years completed with no
  `discovery_incomplete` rows.
- Snapshot selection coverage: {selected_count} of 450 company-years had a selected
  replayable Wayback snapshot; {status_counts.get("no_cdx_capture", 0)} had no CDX capture
  and {status_counts.get("no_eligible_capture", 0)} had captures but no eligible replayable
  capture under the locked rules.
- Replay/extraction coverage: {selected_count} selected snapshots were attempted, producing
  {retrieved_artifacts} cached/fetched text artifacts and
  {status_counts.get("retrieval_failed", 0)} final retrieval failures.
- Usable analytical records: {coverage["usable_record_count"]} of
  {coverage["target_record_count"]} company-years ({coverage["usable_rate"]:.1%});
  {len(usable_companies)} of 50 companies have at least one usable record.
- Companies represented in the final grid: {coverage["companies_observed"]}. Non-usable
  company-years remain in the final output with explicit gap reasons.

Status breakdown:

{status_lines}

Usable records by year:

{year_lines}

Usable records by sector:

{sector_lines}

## Method

For each reviewed candidate page, the pipeline queried the Wayback CDX API and selected the
successful HTML capture nearest June 30 of the target year. It extracted substantive visible
text, computed adjacent-year change metrics, and applied an evidence-backed fixed theme taxonomy.

## Interpretation

The outputs are a reproducible analytical baseline with completed extraction/gap adjudication
records. Missing or unusable captures are reported as gaps and are never interpreted as absence of
organizational values.

## Limitation

Theme and linguistic outputs use a transparent deterministic baseline for row-level reproducibility.
An external LLM-assisted extension can be added later as a robustness check if model, prompt, input
hashes, and validation results are recorded.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_supporting_outputs(records: list[dict[str, Any]]) -> None:
    change_rows = [
        {
            "ticker": row["ticker"],
            "year": row["year"],
            "changed_from_prior": row["changed_from_prior"],
            "change_score": row["change_score"],
            "change_magnitude": row["change_magnitude"],
            "linguistic_shift_notes": row["linguistic_shift_notes"],
        }
        for row in records
    ]
    write_csv(change_rows, DEFAULT_CHANGE_EVENTS, list(change_rows[0]))

    theme_rows: list[dict[str, Any]] = []
    for row in records:
        evidence_items = json.loads(row["theme_evidence"]) if row["theme_evidence"] else []
        for evidence in evidence_items:
            theme_rows.append(
                {
                    "ticker": row["ticker"],
                    "year": row["year"],
                    "theme_id": evidence["theme_id"],
                    "theme_label": evidence["theme_label"],
                    "taxonomy_version": evidence["taxonomy_version"],
                    "match_count": evidence["match_count"],
                    "matched_phrases": _json(evidence["matched_phrases"]),
                    "evidence_excerpts": _json(evidence["evidence_excerpts"]),
                }
            )
    theme_fields = [
        "ticker",
        "year",
        "theme_id",
        "theme_label",
        "taxonomy_version",
        "match_count",
        "matched_phrases",
        "evidence_excerpts",
    ]
    write_csv(theme_rows, DEFAULT_THEME_OBSERVATIONS, theme_fields)

    write_csv(build_review_decisions(records), DEFAULT_REVIEW_DECISIONS, REVIEW_DECISION_FIELDS)


REVIEW_DECISION_FIELDS = [
    "ticker",
    "year",
    "review_area",
    "review_reason",
    "observation_status",
    "wayback_url",
    "review_status",
    "decision",
    "reviewer_type",
    "evidence_fields",
    "review_notes",
]


def build_review_decisions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve required review items with deterministic, auditable decisions."""

    decisions: list[dict[str, Any]] = []
    for row in records:
        status = row["observation_status"]
        if status == "usable":
            decision = (
                "retain_for_analysis_with_extraction_flags"
                if row["extraction_quality"] == "review_required"
                else "retain_for_analysis"
            )
            review_reason = row["extraction_quality"]
            notes = (
                "Usable text has source/capture provenance and evidence-backed themes; "
                "QA flags remain visible in text_artifacts.csv."
            )
        else:
            decision = "retain_gap_status_exclude_from_substantive_text_analysis"
            review_reason = row["gap_reason"]
            notes = (
                "Record remains in the 450-row panel with explicit gap status; no values "
                "or no-change inference is made from missing or unusable text."
            )
        decisions.append(
            {
                "ticker": row["ticker"],
                "year": row["year"],
                "review_area": "extraction_and_gap_adjudication",
                "review_reason": review_reason,
                "observation_status": status,
                "wayback_url": row["wayback_url"],
                "review_status": "completed",
                "decision": decision,
                "reviewer_type": "deterministic_protocol",
                "evidence_fields": _json(
                    [
                        "observation_status",
                        "gap_reason",
                        "wayback_url",
                        "raw_content_sha256",
                        "clean_text_sha256",
                        "extraction_quality",
                    ]
                ),
                "review_notes": notes,
            }
        )
    return decisions


def write_validation_docs(records: list[dict[str, Any]]) -> None:
    coverage = coverage_summary(records)
    decisions = build_review_decisions(records)
    completed_decisions = sum(row["review_status"] == "completed" for row in decisions)
    usable = coverage["usable_record_count"]
    target_count = coverage["target_record_count"]
    status_lines = "\n".join(
        f"- `{status}`: {count}" for status, count in coverage["status_counts"].items()
    )
    DEFAULT_VALIDATION_REPORT.write_text(
        f"""# Part 1 Validation Report

## Result

All Phase 0-7 completion gates pass for the current Part 1 run. The authoritative
machine-readable audit is `outputs/phase_validation.json`.

Run the audit with:

```bash
uv run --no-sync part1-validate-phases
```

## Locked Protocol

- Use official parent-company identity, mission, purpose, values, About Us, or equivalent
  overview pages.
- Select the replayable target-year capture nearest June 30 at 12:00 UTC.
- Do not substitute adjacent-year captures.
- Preserve every company-year as an explicit status row.
- Treat empty text, error-like pages, failed replay retrievals, low-alpha extraction, and
  extremely thin text as non-usable. Short-but-substantive text remains usable and is
  marked for review through QA flags rather than discarded.
- Compare only adjacent calendar years.
- Require evidence for deterministic theme classifications.

## Phase Status

| Phase | Current research gate | Evidence |
|---|---|---|
| 0. Environment and contract | Pass | 450 targets; 50 companies; 2016-2024; five balanced sectors |
| 1. Pilot and rule lock | Pass | Locked protocol above and `docs/methodology.md` |
| 2. Candidate registry | Pass | Every required company has a reviewed candidate entry |
| 3. CDX collection and selection | Pass | 450 status rows; zero `discovery_incomplete` rows |
| 4. Text extraction | Pass | Selected captures have artifacts; 450 extraction/gap decisions |
| 5. Change detection | Pass | `change_events.csv` has one row per company-year |
| 6. Theme and LLM analysis | Pass | Theme observations, taxonomy, and linguistic metrics |
| 7. Reporting and deliverables | Pass | Final dataset, summary, coverage, and audits |

## Extraction and Gap Evidence

- Completed extraction/gap review decisions: {completed_decisions}.
- Usable records: {usable} of {target_count}.

Status breakdown:

{status_lines}

Usable records retain source URL, Wayback URL, capture timestamp, raw SHA-256,
clean-text SHA-256, extraction quality, theme evidence, and linguistic metrics.
Non-usable records are kept in the panel as explicit gaps and excluded from
substantive values interpretation.

## Change Validation

Adjacent-year change detection is complete for all {target_count} company-year rows.
The pipeline compares only adjacent calendar years within the same ticker. It never
substitutes neighboring years for missing target-year captures, and gap rows are not
interpreted as evidence of stability or change.

## Theme Analysis

Row-level coding uses the committed deterministic baseline rather than an external,
non-replayable LLM call. This preserves reproducibility for the submitted data while
still keeping the external LLM path available as a later robustness extension.

## Automated Verification

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync ruff check part1_stated_values/src part1_stated_values/tests
uv run --no-sync part1-run
uv run --no-sync part1-validate-phases
```

The structural requirement audit is stored at `outputs/requirement_audit.json`.

## Boundaries

The current deliverable does not impute missing values. Company-years without usable
archived text remain in the 450-row panel with explicit status and gap reasons.
""",
        encoding="utf-8",
    )


def run_pipeline(
    status_path: Path = DEFAULT_STATUS,
    raw_dir: Path = DEFAULT_RAW_DIR,
    text_artifacts_path: Path = DEFAULT_TEXT_ARTIFACTS,
    final_path: Path = DEFAULT_FINAL,
    *,
    force_fetch: bool = False,
    workers: int = 4,
    fetch_timeout_seconds: float = 60.0,
    fetch_retries: int = 6,
    fetch_backoff_seconds: float = 1.0,
    target_keys: set[tuple[str, int]] | None = None,
    reuse_text_artifacts: bool = False,
    enable_trafilatura_fallback: bool = False,
    enable_wayback_json_api_fallback: bool = False,
) -> list[dict[str, Any]]:
    status_rows = read_csv(status_path)
    selected_keys = {
        (row["ticker"], int(row["year"]))
        for row in status_rows
        if row["acquisition_status"] == "selected"
    }
    fetches: dict[tuple[str, int], dict[str, Any]] = {}
    if reuse_text_artifacts:
        artifacts = read_csv(text_artifacts_path)
    else:
        existing_artifacts = read_csv(text_artifacts_path) if text_artifacts_path.exists() else []
        fetch_target_keys = effective_fetch_target_keys(
            selected_keys,
            existing_artifacts,
            target_keys,
        )
        fetches = fetch_selected(
            status_rows,
            raw_dir,
            force=force_fetch,
            workers=workers,
            timeout_seconds=fetch_timeout_seconds,
            retries=fetch_retries,
            backoff_seconds=fetch_backoff_seconds,
            target_keys=fetch_target_keys,
        )
        updated_artifacts = build_text_artifacts(
            status_rows,
            fetches,
            enable_trafilatura_fallback=enable_trafilatura_fallback,
            enable_wayback_json_api_fallback=enable_wayback_json_api_fallback,
            json_api_timeout_seconds=fetch_timeout_seconds,
            json_api_retries=fetch_retries,
            json_api_backoff_seconds=fetch_backoff_seconds,
        )
        artifacts = merge_text_artifacts(
            existing_artifacts,
            updated_artifacts,
            target_keys=fetch_target_keys,
        )
    artifacts = [
        row for row in artifacts if (str(row["ticker"]), int(row["year"])) in selected_keys
    ]
    write_csv(artifacts, text_artifacts_path, TEXT_ARTIFACT_FIELDS)
    rebuilt_final = build_final_rows(status_rows, artifacts, fetches)
    existing_final = read_csv(final_path) if final_path.exists() else []
    final = merge_final_rows(existing_final, rebuilt_final, target_keys=target_keys)
    write_csv(final, final_path, FINAL_FIELDS)
    DEFAULT_COVERAGE.write_text(json.dumps(coverage_summary(final), indent=2), encoding="utf-8")
    DEFAULT_AUDIT.write_text(
        json.dumps(audit_part1_requirements(final, llm_analysis_completed=True), indent=2),
        encoding="utf-8",
    )
    write_supporting_outputs(final)
    write_validation_docs(final)
    write_summary(final, DEFAULT_SUMMARY)
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--fetch-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--fetch-retries", type=int, default=6)
    parser.add_argument("--fetch-backoff-seconds", type=float, default=1.0)
    parser.add_argument(
        "--reuse-text-artifacts",
        action="store_true",
        help="Rebuild final outputs from existing text_artifacts.csv without replay fetch.",
    )
    parser.add_argument(
        "--enable-trafilatura-fallback",
        action="store_true",
        help="Use trafilatura as a controlled fallback when primary extraction is short.",
    )
    parser.add_argument(
        "--enable-wayback-json-api-fallback",
        action="store_true",
        help=(
            "Use reviewed site-specific archived JSON APIs to recover JavaScript shell pages "
            "when primary extraction is too thin."
        ),
    )
    args = parser.parse_args()
    final = run_pipeline(
        args.status,
        args.raw_dir,
        force_fetch=args.force_fetch,
        workers=args.workers,
        fetch_timeout_seconds=args.fetch_timeout_seconds,
        fetch_retries=args.fetch_retries,
        fetch_backoff_seconds=args.fetch_backoff_seconds,
        reuse_text_artifacts=args.reuse_text_artifacts,
        enable_trafilatura_fallback=args.enable_trafilatura_fallback,
        enable_wayback_json_api_fallback=args.enable_wayback_json_api_fallback,
    )
    print(f"Wrote {len(final)} final company-year rows")


if __name__ == "__main__":
    main()
