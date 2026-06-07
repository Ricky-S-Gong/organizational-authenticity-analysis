"""Run the Part 2 SEC DEF 14A collection and analysis pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from org_auth_part2.analyze import analysis_json, linguistic_metrics
from org_auth_part2.edgar import (
    EdgarClient,
    load_submissions,
    load_ticker_cik_map,
    metadata_dict,
    normalize_ticker,
    select_def14a_for_year_from_rows,
    submission_rows,
)
from org_auth_part2.extract import extract_visible_text, extraction_quality
from org_auth_part2.models import CollectionResult, CompanyYear
from org_auth_part2.targets import (
    DEFAULT_COMPANIES,
    PART2_ROOT,
    TARGET_YEARS,
    build_targets,
    load_companies,
    write_targets,
)

DEFAULT_TARGETS = PART2_ROOT / "config/company_year_targets.csv"
DEFAULT_DATASET = PART2_ROOT / "outputs/part2_company_year.csv"
DEFAULT_COMPACT_DATASET = PART2_ROOT / "outputs/part2_company_year_compact.csv"
DEFAULT_CANDIDATES = PART2_ROOT / "data/processed/filing_candidates.csv"
DEFAULT_DOWNLOAD_LOG = PART2_ROOT / "data/processed/download_log.csv"
DEFAULT_EXTRACTION_LOG = PART2_ROOT / "data/processed/extraction_log.csv"
DEFAULT_MANUAL_REVIEW = PART2_ROOT / "data/review/manual_review_queue.csv"
DEFAULT_COVERAGE = PART2_ROOT / "outputs/coverage_report.json"
DEFAULT_AUDIT = PART2_ROOT / "outputs/requirement_audit.json"
DEFAULT_PROGRESS_LOG = PART2_ROOT / "data/interim/part2_run_progress.jsonl"
DEFAULT_STATE = PART2_ROOT / "data/interim/part2_run_state.json"
DEFAULT_CIK_CACHE = PART2_ROOT / "data/interim/company_tickers.json"
DEFAULT_SUBMISSIONS_DIR = PART2_ROOT / "data/interim/submissions"
DEFAULT_RAW_DIR = PART2_ROOT / "data/raw/filings"
DEFAULT_TEXT_DIR = PART2_ROOT / "data/processed/text"

FIELDNAMES = [
    "ticker",
    "company_name",
    "sector",
    "year",
    "collection_status",
    "gap_reason",
    "cik",
    "form",
    "filing_date",
    "report_date",
    "accession_number",
    "primary_document",
    "source_url",
    "sec_archive_url",
    "raw_file_path",
    "raw_file_bytes",
    "raw_content_sha256",
    "clean_text_sha256",
    "text_path",
    "page_text_clean",
    "extraction_quality",
    "word_count",
    "sentence_count",
    "theme_categories",
    "theme_evidence",
    "linguistic_metrics",
    "analyst_notes",
]


class ProgressLogger:
    """Append-only JSONL logger for real-time monitoring and rerun audits."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, stage: str, status: str, **payload: Any) -> None:
        """Record one structured progress event without mutating prior events."""

        row = {
            "timestamp": datetime.now(UTC).isoformat(),
            "stage": stage,
            "status": status,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def _sha256_bytes(content: bytes) -> str:
    """Hash raw filing bytes so stored artifacts can be integrity-checked."""

    return hashlib.sha256(content).hexdigest()


def _sha256_text(text: str) -> str:
    """Hash extracted text separately from raw HTML for extraction auditability."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_name(ticker: str, year: int, accession: str, suffix: str) -> str:
    """Create deterministic artifact filenames from company-year filing IDs."""

    safe_ticker = normalize_ticker(ticker).lower()
    safe_accession = accession.replace("-", "")
    return f"{safe_ticker}_{year}_{safe_accession}{suffix}"


def read_targets(path: Path) -> list[CompanyYear]:
    """Read the persisted company-year grid used by the collection run."""

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        CompanyYear(
            ticker=row["ticker"],
            company_name=row["company_name"],
            sector=row["sector"],
            year=int(row["year"]),
        )
        for row in rows
    ]


def write_results(results: list[CollectionResult], path: Path) -> None:
    """Write the full dataset, including extracted text for analysis reruns."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))


def write_compact_results(results: list[CollectionResult], path: Path) -> None:
    """Write a shareable dataset variant that excludes the large text column."""

    compact_fields = [field for field in FIELDNAMES if field != "page_text_clean"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=compact_fields)
        writer.writeheader()
        for result in results:
            row = asdict(result)
            writer.writerow({field: row[field] for field in compact_fields})


def write_candidates(path: Path, metadata_rows: list[dict[str, Any]]) -> None:
    """Persist selected filing metadata for transparent selection review."""

    if not metadata_rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(metadata_rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata_rows)


def collect_one(
    target: CompanyYear,
    *,
    client: EdgarClient,
    ticker_cik: dict[str, str],
    submissions_dir: Path,
    raw_dir: Path,
    text_dir: Path,
    logger: ProgressLogger,
    minimum_words: int,
) -> tuple[CollectionResult, dict[str, Any] | None]:
    """Collect and analyze one company-year while preserving every failure mode."""

    normalized = normalize_ticker(target.ticker)
    cik = ticker_cik.get(normalized, "")
    if not cik:
        # Missing CIKs are panel gaps, not exceptions: downstream code needs the
        # row so coverage denominators remain anchored to the original 450 targets.
        logger.event("company_year", "missing_cik", ticker=target.ticker, year=target.year)
        return (
            CollectionResult(
                ticker=target.ticker,
                company_name=target.company_name,
                sector=target.sector,
                year=target.year,
                collection_status="missing",
                gap_reason="ticker_not_found_in_sec_ticker_cik_map",
            ),
            None,
        )

    try:
        submissions = load_submissions(client, cik, submissions_dir / f"CIK{cik}.json")
    except Exception as exc:  # noqa: BLE001 - logged as auditable collection status
        logger.event(
            "company_year",
            "submission_failed",
            ticker=target.ticker,
            year=target.year,
            cik=cik,
            error=str(exc),
        )
        return (
            CollectionResult(
                ticker=target.ticker,
                company_name=target.company_name,
                sector=target.sector,
                year=target.year,
                collection_status="failed",
                gap_reason=f"submission_api_failed: {exc}",
                cik=cik,
            ),
            None,
        )

    rows = submission_rows(client, cik, submissions, submissions_dir)
    metadata = select_def14a_for_year_from_rows(
        ticker=target.ticker,
        cik=cik,
        company_name=target.company_name,
        year=target.year,
        rows=rows,
    )
    if metadata is None:
        # A missing calendar-year DEF 14A remains in the dataset with a controlled
        # reason instead of being imputed or treated as zero disclosure emphasis.
        logger.event(
            "company_year",
            "missing_def14a",
            ticker=target.ticker,
            year=target.year,
            cik=cik,
        )
        return (
            CollectionResult(
                ticker=target.ticker,
                company_name=target.company_name,
                sector=target.sector,
                year=target.year,
                collection_status="missing",
                gap_reason="no_def14a_filing_for_calendar_year",
                cik=cik,
            ),
            None,
        )

    try:
        content, content_type = client.get_bytes(metadata.sec_archive_url)
    except Exception as exc:  # noqa: BLE001 - logged as auditable collection status
        logger.event(
            "company_year",
            "download_failed",
            ticker=target.ticker,
            year=target.year,
            cik=cik,
            accession_number=metadata.accession_number,
            error=str(exc),
        )
        return (
            CollectionResult(
                ticker=target.ticker,
                company_name=target.company_name,
                sector=target.sector,
                year=target.year,
                collection_status="failed",
                gap_reason=f"download_failed: {exc}",
                cik=cik,
                **{
                    key: value
                    for key, value in metadata_dict(metadata).items()
                    if key not in {"ticker", "company_name", "year", "cik"}
                },
            ),
            metadata_dict(metadata),
        )

    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    # Store both raw and clean artifacts. The raw hash supports source integrity;
    # the clean-text hash supports reproducible text-mining reruns.
    raw_suffix = Path(metadata.primary_document).suffix or ".html"
    raw_path = raw_dir / _safe_name(
        target.ticker,
        target.year,
        metadata.accession_number,
        raw_suffix,
    )
    raw_path.write_bytes(content)
    clean_text = extract_visible_text(content, content_type)
    quality = extraction_quality(clean_text, minimum_words)
    text_path = text_dir / _safe_name(target.ticker, target.year, metadata.accession_number, ".txt")
    text_path.write_text(clean_text, encoding="utf-8")
    raw_hash = _sha256_bytes(content)
    text_hash = _sha256_text(clean_text)
    metrics = linguistic_metrics(clean_text)
    theme_categories, theme_evidence, metrics_json = analysis_json(clean_text)

    # Low-quality extractions are retained for review rather than promoted to
    # successful observations. This protects descriptive results from tiny or
    # index-only artifacts while keeping the audit trail complete.
    status = "collected" if quality == "usable" else "needs_review"
    gap_reason = "" if quality == "usable" else quality
    logger.event(
        "company_year",
        status,
        ticker=target.ticker,
        year=target.year,
        cik=cik,
        accession_number=metadata.accession_number,
        word_count=metrics["word_count"],
        extraction_quality=quality,
    )
    return (
        CollectionResult(
            ticker=target.ticker,
            company_name=target.company_name,
            sector=target.sector,
            year=target.year,
            collection_status=status,
            gap_reason=gap_reason,
            cik=cik,
            form=metadata.form,
            filing_date=metadata.filing_date,
            report_date=metadata.report_date,
            accession_number=metadata.accession_number,
            primary_document=metadata.primary_document,
            source_url=metadata.source_url,
            sec_archive_url=metadata.sec_archive_url,
            raw_file_path=str(raw_path),
            raw_file_bytes=len(content),
            raw_content_sha256=raw_hash,
            clean_text_sha256=text_hash,
            text_path=str(text_path),
            page_text_clean=clean_text,
            extraction_quality=quality,
            word_count=metrics["word_count"],
            sentence_count=metrics["sentence_count"],
            theme_categories=theme_categories,
            theme_evidence=theme_evidence,
            linguistic_metrics=metrics_json,
            analyst_notes=(
                "Automated SEC DEF 14A collection; review flagged rows before making "
                "substantive claims."
            ),
        ),
        metadata_dict(metadata),
    )


def write_manual_review(results: list[CollectionResult], path: Path) -> None:
    """Write a queue of non-collected rows that require manual inspection."""

    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "ticker": result.ticker,
            "year": result.year,
            "collection_status": result.collection_status,
            "gap_reason": result.gap_reason,
            "sec_archive_url": result.sec_archive_url,
            "review_reason": result.gap_reason or "sample_for_quality_review",
            "review_decision": "",
            "review_notes": "",
        }
        for result in results
        if result.collection_status != "collected"
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "ticker",
            "year",
            "collection_status",
            "gap_reason",
            "sec_archive_url",
            "review_reason",
            "review_decision",
            "review_notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_download_log(results: list[CollectionResult], path: Path) -> None:
    """Write source and raw-artifact fields needed to audit downloads."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "year",
        "collection_status",
        "sec_archive_url",
        "raw_file_path",
        "raw_file_bytes",
        "raw_content_sha256",
        "gap_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({field: getattr(result, field) for field in fieldnames})


def write_extraction_log(results: list[CollectionResult], path: Path) -> None:
    """Write text extraction hashes, quality labels, and size diagnostics."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "year",
        "collection_status",
        "raw_content_sha256",
        "text_path",
        "clean_text_sha256",
        "extraction_quality",
        "word_count",
        "sentence_count",
        "gap_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({field: getattr(result, field) for field in fieldnames})


def coverage_report(results: list[CollectionResult]) -> dict[str, Any]:
    """Summarize collection coverage overall and by sector."""

    by_status: dict[str, int] = {}
    by_sector: dict[str, dict[str, int]] = {}
    for result in results:
        by_status[result.collection_status] = by_status.get(result.collection_status, 0) + 1
        sector_counts = by_sector.setdefault(result.sector, {})
        sector_counts[result.collection_status] = sector_counts.get(result.collection_status, 0) + 1
    collected = by_status.get("collected", 0)
    return {
        "document_type": "DEF 14A proxy statement",
        "source": "SEC EDGAR submissions API and Archives",
        "target_rows": len(results),
        "collected_rows": collected,
        "coverage_rate": round(collected / len(results), 4) if results else 0,
        "status_counts": by_status,
        "sector_status_counts": by_sector,
    }


def requirement_audit(results: list[CollectionResult]) -> dict[str, Any]:
    """Check whether generated outputs satisfy the Part 2 research contract."""

    target_rows = len(results)
    collected = [row for row in results if row.collection_status == "collected"]
    successful_have_evidence = all(
        row.cik
        and row.accession_number
        and row.sec_archive_url
        and row.raw_file_path
        and row.raw_file_bytes > 0
        and row.raw_content_sha256
        and row.clean_text_sha256
        and row.word_count >= 1000
        for row in collected
    )
    all_status_documented = all(
        row.collection_status and (row.collection_status == "collected" or row.gap_reason)
        for row in results
    )
    return {
        "same_50_company_grid": target_rows == 450,
        "year_window": sorted({row.year for row in results}) == list(TARGET_YEARS),
        "one_document_type": True,
        "document_type": "DEF 14A",
        "free_reproducible_source": True,
        "all_rows_have_status_or_gap": all_status_documented,
        "successful_rows_have_source_hash_and_text_metrics": successful_have_evidence,
        "collected_rows": len(collected),
        "target_rows": target_rows,
        "manual_review_required_rows": sum(
            1 for row in results if row.collection_status != "collected"
        ),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable, sorted JSON for human-readable audit artifacts."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_pipeline(args: argparse.Namespace) -> list[CollectionResult]:
    """Run collection end to end and write all Part 2 collection artifacts."""

    logger = ProgressLogger(args.progress_log)
    logger.event("run", "started", limit=args.limit, ticker=args.ticker)
    if not args.targets.exists():
        targets = build_targets(load_companies(args.companies))
        write_targets(targets, args.targets)
    targets = read_targets(args.targets)
    if args.ticker:
        requested = {
            normalize_ticker(ticker.strip()) for ticker in args.ticker.split(",") if ticker.strip()
        }
        targets = [target for target in targets if normalize_ticker(target.ticker) in requested]
    if args.limit:
        targets = targets[: args.limit]

    # Keep a single HTTP client for the run so headers, timeouts, and throttling
    # are consistent across ticker lookup, metadata, and document downloads.
    client = EdgarClient(timeout_seconds=args.timeout_seconds, sleep_seconds=args.sleep_seconds)
    results: list[CollectionResult] = []
    candidate_rows: list[dict[str, Any]] = []
    try:
        ticker_cik = load_ticker_cik_map(client, args.cik_cache)
        for index, target in enumerate(targets, start=1):
            logger.event(
                "company_year",
                "started",
                index=index,
                total=len(targets),
                ticker=target.ticker,
                year=target.year,
            )
            result, metadata = collect_one(
                target,
                client=client,
                ticker_cik=ticker_cik,
                submissions_dir=args.submissions_dir,
                raw_dir=args.raw_dir,
                text_dir=args.text_dir,
                logger=logger,
                minimum_words=args.minimum_words,
            )
            results.append(result)
            if metadata:
                candidate_rows.append(metadata)
            write_json(
                args.state_file,
                {
                    "latest_ticker": target.ticker,
                    "latest_year": target.year,
                    "completed": index,
                    "total": len(targets),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
    finally:
        client.close()

    write_results(results, args.output)
    write_compact_results(results, args.compact_output)
    write_candidates(args.candidates, candidate_rows)
    write_download_log(results, args.download_log)
    write_extraction_log(results, args.extraction_log)
    write_manual_review(results, args.manual_review)
    write_json(args.coverage, coverage_report(results))
    write_json(args.audit, requirement_audit(results))
    logger.event(
        "run",
        "completed",
        rows=len(results),
        collected=sum(1 for result in results if result.collection_status == "collected"),
    )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect and analyze Part 2 SEC DEF 14A disclosures."
    )
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--compact-output", type=Path, default=DEFAULT_COMPACT_DATASET)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--download-log", type=Path, default=DEFAULT_DOWNLOAD_LOG)
    parser.add_argument("--extraction-log", type=Path, default=DEFAULT_EXTRACTION_LOG)
    parser.add_argument("--manual-review", type=Path, default=DEFAULT_MANUAL_REVIEW)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--progress-log", type=Path, default=DEFAULT_PROGRESS_LOG)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--cik-cache", type=Path, default=DEFAULT_CIK_CACHE)
    parser.add_argument("--submissions-dir", type=Path, default=DEFAULT_SUBMISSIONS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--text-dir", type=Path, default=DEFAULT_TEXT_DIR)
    parser.add_argument("--ticker", help="Comma-separated ticker filter for smoke runs.")
    parser.add_argument("--limit", type=int, help="Limit target rows for smoke runs.")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--sleep-seconds", type=float, default=0.15)
    parser.add_argument("--minimum-words", type=int, default=1000)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = run_pipeline(args)
    print(
        json.dumps(
            {
                "rows": len(results),
                "collected": sum(
                    1 for result in results if result.collection_status == "collected"
                ),
                "output": str(args.output),
                "progress_log": str(args.progress_log),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
