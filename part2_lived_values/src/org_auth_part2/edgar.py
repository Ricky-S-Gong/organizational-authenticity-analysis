"""Free SEC EDGAR access helpers for Part 2 DEF 14A collection."""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx

from org_auth_part2.models import FilingMetadata

SEC_HEADERS = {
    "User-Agent": "organizational-authenticity-research/0.1 contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}
TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SUBMISSIONS_FILE_URL = "https://data.sec.gov/submissions/{name}"
ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"


class EdgarClient:
    def __init__(self, *, timeout_seconds: float = 30, sleep_seconds: float = 0.15) -> None:
        self.timeout_seconds = timeout_seconds
        self.sleep_seconds = sleep_seconds
        self._client = httpx.Client(
            headers=SEC_HEADERS,
            timeout=timeout_seconds,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def get_json(self, url: str) -> dict[str, Any]:
        time.sleep(self.sleep_seconds)
        response = self._client.get(url)
        response.raise_for_status()
        return response.json()

    def get_bytes(self, url: str) -> tuple[bytes, str]:
        time.sleep(self.sleep_seconds)
        response = self._client.get(url)
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "")


def normalize_ticker(ticker: str) -> str:
    return ticker.upper().replace(".", "-")


def load_ticker_cik_map(client: EdgarClient, cache_path: Path | None = None) -> dict[str, str]:
    if cache_path and cache_path.exists():
        import json

        with cache_path.open(encoding="utf-8") as handle:
            cached = json.load(handle)
        return {
            normalize_ticker(row["ticker"]): str(row["cik_str"]).zfill(10)
            for row in cached.values()
        }

    data = client.get_json(TICKER_CIK_URL)
    if cache_path:
        import json

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {normalize_ticker(row["ticker"]): str(row["cik_str"]).zfill(10) for row in data.values()}


def _columnar_rows(recent: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(recent)
    if not keys:
        return []
    size = len(recent[keys[0]])
    return [{key: recent[key][idx] for key in keys} for idx in range(size)]


def load_submissions(
    client: EdgarClient,
    cik: str,
    cache_path: Path | None = None,
) -> dict[str, Any]:
    if cache_path and cache_path.exists():
        import json

        with cache_path.open(encoding="utf-8") as handle:
            return json.load(handle)
    data = client.get_json(SUBMISSIONS_URL.format(cik=cik))
    if cache_path:
        import json

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def load_submission_file(
    client: EdgarClient,
    name: str,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    cache_path = cache_dir / name if cache_dir else None
    if cache_path and cache_path.exists():
        import json

        with cache_path.open(encoding="utf-8") as handle:
            return json.load(handle)
    data = client.get_json(SUBMISSIONS_FILE_URL.format(name=name))
    if cache_path:
        import json

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def filing_document_url(cik: str, accession_number: str, primary_document: str) -> str:
    cik_int = str(int(cik))
    accession_compact = accession_number.replace("-", "")
    return f"{ARCHIVE_BASE}/{cik_int}/{accession_compact}/{primary_document}"


def submission_rows(
    client: EdgarClient,
    cik: str,
    submissions: dict[str, Any],
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    rows = _columnar_rows(submissions.get("filings", {}).get("recent", {}))
    for file_info in submissions.get("filings", {}).get("files", []):
        name = file_info.get("name")
        if not name:
            continue
        data = load_submission_file(client, name, cache_dir)
        rows.extend(_columnar_rows(data))
    return rows


def select_def14a_for_year_from_rows(
    *,
    ticker: str,
    cik: str,
    company_name: str,
    year: int,
    rows: list[dict[str, Any]],
    include_supplements: bool = False,
) -> FilingMetadata | None:
    forms = {"DEF 14A"}
    if include_supplements:
        forms.add("DEFA14A")
    candidates = [
        row
        for row in rows
        if row.get("form") in forms
        and str(row.get("filingDate", "")).startswith(str(year))
        and row.get("accessionNumber")
        and row.get("primaryDocument")
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            row.get("form") != "DEF 14A",
            row.get("filingDate", ""),
            row.get("accessionNumber", ""),
        )
    )
    selected = candidates[0]
    url = filing_document_url(cik, selected["accessionNumber"], selected["primaryDocument"])
    return FilingMetadata(
        ticker=ticker,
        cik=cik,
        company_name=company_name,
        year=year,
        form=selected.get("form", ""),
        filing_date=selected.get("filingDate", ""),
        report_date=selected.get("reportDate", ""),
        accession_number=selected.get("accessionNumber", ""),
        primary_document=selected.get("primaryDocument", ""),
        source_url=SUBMISSIONS_URL.format(cik=cik),
        sec_archive_url=url,
    )


def select_def14a_for_year(
    *,
    ticker: str,
    cik: str,
    company_name: str,
    year: int,
    submissions: dict[str, Any],
    include_supplements: bool = False,
) -> FilingMetadata | None:
    rows = _columnar_rows(submissions.get("filings", {}).get("recent", {}))
    return select_def14a_for_year_from_rows(
        ticker=ticker,
        cik=cik,
        company_name=company_name,
        year=year,
        rows=rows,
        include_supplements=include_supplements,
    )
def metadata_dict(metadata: FilingMetadata) -> dict[str, Any]:
    return asdict(metadata)
