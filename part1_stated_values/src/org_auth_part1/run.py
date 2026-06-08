"""Run the complete Part 1 workflow from inputs to validated deliverables."""

import argparse
import csv
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from org_auth_part1.acquire import (
    CANDIDATE_FIELDS,
    DEFAULT_CANDIDATE_OUTPUT,
    DEFAULT_STATUS_OUTPUT,
    STATUS_FIELDS,
    build_annual_outputs,
    write_csv,
)
from org_auth_part1.discover import (
    DEFAULT_AUGMENTED_PAGE_CANDIDATES,
    DEFAULT_CACHE_DIR,
    DEFAULT_HISTORICAL_CANDIDATES,
    DEFAULT_HISTORICAL_DISCOVERY_AUDIT,
    DEFAULT_PAGE_CANDIDATES,
    DEFAULT_QUERY_LOG,
    discover_candidates,
    discover_historical_page_candidates,
    merge_candidate_files,
    query_log_rows,
    write_query_log,
)
from org_auth_part1.phase_validation import validate_phases
from org_auth_part1.pipeline import DEFAULT_FINAL, run_pipeline
from org_auth_part1.registry import DEFAULT_CANDIDATES, load_candidates, validate_registry
from org_auth_part1.targets import DEFAULT_COMPANIES, DEFAULT_OUTPUT, build_targets, load_companies
from org_auth_part1.targets import write_targets as write_target_grid
from org_auth_part1.validate import build_requirement_audit

DEFAULT_PROGRESS_LOG = Path("part1_stated_values/data/interim/part1_run_progress.jsonl")
DEFAULT_STATE_FILE = Path("part1_stated_values/data/interim/part1_run_state.json")
RECOVERABLE_FINAL_STATUSES = {"insufficient_substantive_text", "retrieval_failed"}
HISTORICAL_DISCOVERY_TARGET_STATUSES = {"discovery_incomplete", "no_cdx_capture"}


@dataclass
class RunLogger:
    """Append-only JSONL progress logger plus a one-record resume/status pointer."""

    progress_log: Path
    state_file: Path
    started_at: float = time.monotonic()

    def event(self, stage: str, status: str, **payload: Any) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "elapsed_seconds": round(time.monotonic() - self.started_at, 3),
            "stage": stage,
            "status": status,
            **payload,
        }
        self.progress_log.parent.mkdir(parents=True, exist_ok=True)
        with self.progress_log.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True) + "\n")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(record, sort_keys=True), flush=True)


def load_nonusable_keys(final_path: Path = DEFAULT_FINAL) -> set[tuple[str, int]]:
    """Return company-years that should be refreshed in an incremental run."""
    if not final_path.exists():
        return set()
    with final_path.open(newline="", encoding="utf-8") as file:
        return {
            (row["ticker"], int(row["year"]))
            for row in csv.DictReader(file)
            if row.get("observation_status") != "usable"
        }


def load_status_keys(statuses: set[str], final_path: Path = DEFAULT_FINAL) -> set[tuple[str, int]]:
    """Return company-years whose current final status is in the requested set."""
    if not final_path.exists():
        return set()
    with final_path.open(newline="", encoding="utf-8") as file:
        return {
            (row["ticker"], int(row["year"]))
            for row in csv.DictReader(file)
            if row.get("observation_status") in statuses
        }


def parse_only_statuses(values: list[str]) -> set[str] | None:
    """Parse repeatable and comma-separated --only-status values."""
    statuses = {status.strip() for value in values for status in value.split(",") if status.strip()}
    return statuses or None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _key(row: dict[str, Any]) -> tuple[str, int]:
    return str(row["ticker"]), int(row["year"])


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def apply_alternate_capture_recovery(
    status_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    final_rows: list[dict[str, Any]],
    *,
    target_keys: set[tuple[str, int]] | None = None,
) -> tuple[list[dict[str, Any]], set[tuple[str, int]]]:
    """Select the next same-year replay candidate for rows with bad retrieved text.

    Recovery never changes company-years that are already usable or outside the
    requested incremental scope. It advances to the next ranked capture so the choice
    remains traceable through ``annual_snapshot_candidates.csv``.
    """
    final_by_key = {_key(row): row for row in final_rows}
    candidates_by_key: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in candidate_rows:
        if _truthy(row.get("eligible")):
            candidates_by_key.setdefault(_key(row), []).append(row)
    for rows in candidates_by_key.values():
        rows.sort(key=lambda item: int(item["rank"]))

    recovered_keys: set[tuple[str, int]] = set()
    updated_rows: list[dict[str, Any]] = []
    for row in status_rows:
        key = _key(row)
        final = final_by_key.get(key, {})
        attempted_url = str(row.get("selected_replay_url") or final.get("wayback_url") or "")
        should_recover = (
            final.get("observation_status") in RECOVERABLE_FINAL_STATUSES
            and attempted_url
            and (target_keys is None or key in target_keys)
        )
        if not should_recover:
            updated_rows.append(row)
            continue

        current_rank = next(
            (
                int(candidate["rank"])
                for candidate in candidates_by_key.get(key, [])
                if candidate.get("replay_url") == attempted_url
            ),
            0,
        )
        alternate = next(
            (
                candidate
                for candidate in candidates_by_key.get(key, [])
                if candidate.get("replay_url")
                and candidate["replay_url"] != attempted_url
                and int(candidate["rank"]) > current_rank
            ),
            None,
        )
        if alternate is None:
            updated_rows.append(row)
            continue

        replacement = dict(row)
        replacement.update(
            {
                "acquisition_status": "selected",
                "failure_reason": "",
                "selected_capture_timestamp": alternate["capture_timestamp"],
                "selected_original_url": alternate["original_url"],
                "selected_replay_url": alternate["replay_url"],
            }
        )
        updated_rows.append(replacement)
        recovered_keys.add(key)
    return updated_rows, recovered_keys


def merge_query_log_rows(
    existing_path: Path, new_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge incremental CDX query-log rows with the existing full query log."""
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    if existing_path.exists():
        with existing_path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                rows[(row["ticker"], row["candidate_url"], str(row["year"]))] = row
    for row in new_rows:
        rows[(str(row["ticker"]), str(row["candidate_url"]), str(row["year"]))] = row
    return [rows[key] for key in sorted(rows, key=lambda item: (item[0], int(item[2]), item[1]))]


def run_all(
    *,
    companies_path: Path = DEFAULT_COMPANIES,
    candidates_path: Path = DEFAULT_CANDIDATES,
    targets_path: Path = DEFAULT_OUTPUT,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    query_log_path: Path = DEFAULT_QUERY_LOG,
    candidate_output: Path = DEFAULT_CANDIDATE_OUTPUT,
    status_output: Path = DEFAULT_STATUS_OUTPUT,
    discovery_retries: int = 5,
    timeout_seconds: float = 120.0,
    backoff_seconds: float = 1.0,
    force_discovery: bool = False,
    prefix_fallback: bool = True,
    replay_retries: int = 3,
    workers: int = 4,
    fetch_timeout_seconds: float = 60.0,
    fetch_retries: int = 6,
    fetch_backoff_seconds: float = 1.0,
    force_fetch: bool = False,
    only_nonusable: bool = False,
    only_statuses: set[str] | None = None,
    alternate_recovery_passes: int = 2,
    enable_trafilatura_fallback: bool = False,
    enable_wayback_json_api_fallback: bool = False,
    discover_historical_urls: bool = False,
    discover_url_variants_only: bool = False,
    discover_domain_cdx_urls: bool = False,
    require_url_variant_cdx_capture: bool = False,
    url_variant_probe_retries: int = 3,
    url_variant_probe_backoff_seconds: float = 2.0,
    url_variant_probe_sleep_seconds: float = 0.0,
    historical_timeout_seconds: float = 15.0,
    historical_workers: int = 4,
    historical_candidates_path: Path = DEFAULT_HISTORICAL_CANDIDATES,
    historical_discovery_audit_path: Path = DEFAULT_HISTORICAL_DISCOVERY_AUDIT,
    augmented_candidates_path: Path = DEFAULT_AUGMENTED_PAGE_CANDIDATES,
    progress_log: Path = DEFAULT_PROGRESS_LOG,
    state_file: Path = DEFAULT_STATE_FILE,
) -> dict[str, Any]:
    """Execute the complete reproducible workflow once over all configured companies.

    The orchestration always rebuilds deterministic local artifacts such as the target
    grid and annual selection table. Network-heavy stages accept ``target_keys`` so
    failed rows can be retried without re-fetching company-years that already have
    usable text.
    """

    logger = RunLogger(progress_log=progress_log, state_file=state_file)
    logger.event("run", "started")

    if only_statuses:
        target_keys = load_status_keys(only_statuses)
    elif only_nonusable:
        target_keys = load_nonusable_keys(DEFAULT_FINAL)
    else:
        target_keys = None
    if only_nonusable or only_statuses:
        logger.event(
            "incremental_scope",
            "completed",
            target_company_years=len(target_keys),
            source=str(DEFAULT_FINAL),
            statuses=sorted(only_statuses) if only_statuses else "nonusable",
        )

    logger.event("target_grid", "started", output=str(targets_path))
    targets = build_targets(load_companies(companies_path))
    write_target_grid(targets, targets_path)
    logger.event("target_grid", "completed", rows=len(targets), output=str(targets_path))

    active_candidates_path = candidates_path
    historical_generated_rows: list[dict[str, Any]] = []
    historical_audit_rows: list[dict[str, Any]] = []
    if discover_historical_urls:
        # Historical URL discovery is intentionally limited to rows that failed because
        # current candidate URLs had no usable same-year CDX evidence.
        historical_target_keys = load_status_keys(HISTORICAL_DISCOVERY_TARGET_STATUSES)
        if target_keys is not None:
            historical_target_keys &= target_keys
        logger.event(
            "historical_url_discovery",
            "started",
            target_company_years=len(historical_target_keys),
            output=str(historical_candidates_path),
            audit=str(historical_discovery_audit_path),
        )
        historical_generated_rows, historical_audit_rows = discover_historical_page_candidates(
            companies_path,
            candidates_path,
            historical_candidates_path,
            historical_discovery_audit_path,
            target_keys=historical_target_keys,
            timeout_seconds=historical_timeout_seconds,
            workers=historical_workers,
            enable_homepage_link_discovery=not discover_url_variants_only,
            enable_domain_cdx_discovery=discover_domain_cdx_urls,
            require_url_variant_cdx_capture=require_url_variant_cdx_capture,
            url_variant_probe_retries=url_variant_probe_retries,
            url_variant_probe_backoff_seconds=url_variant_probe_backoff_seconds,
            url_variant_probe_sleep_seconds=url_variant_probe_sleep_seconds,
            progress_callback=lambda event: logger.event(
                event.pop("stage"), event.pop("status"), **event
            ),
        )
        merged_rows = merge_candidate_files(
            candidates_path, historical_candidates_path, augmented_candidates_path
        )
        active_candidates_path = augmented_candidates_path
        logger.event(
            "historical_url_discovery",
            "completed",
            generated_candidates=len(historical_generated_rows),
            audit_rows=len(historical_audit_rows),
            augmented_candidates=len(merged_rows),
            augmented_candidates_path=str(augmented_candidates_path),
        )

    logger.event("registry", "started", candidates=str(active_candidates_path))
    registry_summary = validate_registry(load_candidates(active_candidates_path), companies_path)
    logger.event("registry", "completed", **registry_summary)

    logger.event(
        "cdx_discovery",
        "started",
        cache_dir=str(cache_dir),
        retries=discovery_retries,
        timeout_seconds=timeout_seconds,
        prefix_fallback=prefix_fallback,
        force=force_discovery,
    )
    discovery_records = discover_candidates(
        active_candidates_path,
        cache_dir,
        retries=discovery_retries,
        backoff_seconds=backoff_seconds,
        timeout_seconds=timeout_seconds,
        force=force_discovery,
        prefix_fallback=prefix_fallback,
        availability_fallback=enable_wayback_json_api_fallback,
        target_keys=target_keys,
        progress_callback=lambda event: logger.event(
            event.pop("stage"), event.pop("status"), **event
        ),
    )
    discovered_query_rows = query_log_rows(discovery_records, cache_dir)
    query_rows = (
        merge_query_log_rows(query_log_path, discovered_query_rows)
        if target_keys is not None
        else discovered_query_rows
    )
    write_query_log(query_rows, query_log_path)
    logger.event(
        "cdx_discovery",
        "completed",
        candidates=len(discovery_records),
        target_company_years=len(target_keys) if target_keys is not None else len(targets),
        query_log=str(query_log_path),
    )

    logger.event("snapshot_selection", "started")
    candidate_rows, status_rows = build_annual_outputs(
        active_candidates_path, targets_path, cache_dir
    )
    write_csv(candidate_rows, candidate_output, CANDIDATE_FIELDS)
    write_csv(status_rows, status_output, STATUS_FIELDS)
    logger.event(
        "snapshot_selection",
        "completed",
        annual_candidates=len(candidate_rows),
        annual_statuses=len(status_rows),
    )

    replay_runs = max(1, replay_retries)
    final_rows = []
    for run_index in range(1, replay_runs + 1):
        logger.event(
            "replay_extraction",
            "started",
            run_index=run_index,
            runs=replay_runs,
            workers=workers,
            fetch_timeout_seconds=fetch_timeout_seconds,
            fetch_retries=fetch_retries,
            force_fetch=force_fetch,
        )
        final_rows = run_pipeline(
            status_output,
            workers=workers,
            fetch_timeout_seconds=fetch_timeout_seconds,
            fetch_retries=fetch_retries,
            fetch_backoff_seconds=fetch_backoff_seconds,
            force_fetch=force_fetch,
            target_keys=target_keys,
            enable_trafilatura_fallback=enable_trafilatura_fallback,
            enable_wayback_json_api_fallback=enable_wayback_json_api_fallback,
        )
        logger.event(
            "replay_extraction",
            "completed",
            run_index=run_index,
            runs=replay_runs,
            final_rows=len(final_rows),
        )

    for recovery_index in range(1, max(0, alternate_recovery_passes) + 1):
        # A replay can succeed technically but yield an error shell or too little text.
        # This loop tries the next ranked capture and then re-runs extraction only for
        # those recovered keys.
        status_rows, recovery_keys = apply_alternate_capture_recovery(
            read_csv_rows(status_output),
            read_csv_rows(candidate_output),
            read_csv_rows(DEFAULT_FINAL),
            target_keys=target_keys,
        )
        logger.event(
            "alternate_capture_recovery",
            "completed" if recovery_keys else "skipped",
            run_index=recovery_index,
            runs=alternate_recovery_passes,
            target_company_years=len(recovery_keys),
        )
        if not recovery_keys:
            break
        write_csv(status_rows, status_output, STATUS_FIELDS)
        final_rows = run_pipeline(
            status_output,
            workers=workers,
            fetch_timeout_seconds=fetch_timeout_seconds,
            fetch_retries=fetch_retries,
            fetch_backoff_seconds=fetch_backoff_seconds,
            force_fetch=True,
            target_keys=recovery_keys,
            enable_trafilatura_fallback=enable_trafilatura_fallback,
            enable_wayback_json_api_fallback=enable_wayback_json_api_fallback,
        )

    logger.event("validation", "started")
    requirement_audit = build_requirement_audit(targets_path, DEFAULT_FINAL)
    phase_audit = validate_phases(Path("."))
    summary = {
        "targets": len(targets),
        "registry": registry_summary,
        "historical_discovery": {
            "enabled": discover_historical_urls,
            "url_variants_only": discover_url_variants_only,
            "domain_cdx_enabled": discover_domain_cdx_urls,
            "url_variant_cdx_capture_required": require_url_variant_cdx_capture,
            "url_variant_probe_retries": url_variant_probe_retries,
            "url_variant_probe_backoff_seconds": url_variant_probe_backoff_seconds,
            "url_variant_probe_sleep_seconds": url_variant_probe_sleep_seconds,
            "generated_candidates": len(historical_generated_rows),
            "audit_rows": len(historical_audit_rows),
        },
        "discovery_candidates": len(discovery_records),
        "annual_candidates": len(candidate_rows),
        "annual_statuses": len(status_rows),
        "final_rows": len(final_rows),
        "requirement_audit_passed": requirement_audit["passed"],
        "phase_validation_passed": phase_audit["passed"],
        "phase_validation": phase_audit,
    }
    logger.event(
        "validation",
        "completed",
        requirement_audit_passed=bool(requirement_audit["passed"]),
        phase_validation_passed=bool(phase_audit["passed"]),
    )
    logger.event("run", "completed")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_PAGE_CANDIDATES)
    parser.add_argument("--targets", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--query-log", type=Path, default=DEFAULT_QUERY_LOG)
    parser.add_argument("--discovery-retries", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--force-discovery", action="store_true")
    parser.add_argument("--no-prefix-fallback", action="store_true")
    parser.add_argument("--replay-retries", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--fetch-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--fetch-retries", type=int, default=6)
    parser.add_argument("--fetch-backoff-seconds", type=float, default=1.0)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--alternate-recovery-passes", type=int, default=2)
    parser.add_argument("--enable-trafilatura-fallback", action="store_true")
    parser.add_argument("--enable-wayback-json-api-fallback", action="store_true")
    parser.add_argument(
        "--discover-historical-urls",
        action="store_true",
        help="Try to recover no-CDX rows by discovering same-year links from archived homepages.",
    )
    parser.add_argument(
        "--discover-domain-cdx-urls",
        action="store_true",
        help=(
            "Also try broader same-year domain-level CDX discovery. This is off by default "
            "because it can produce low-precision regional or marketing URLs."
        ),
    )
    parser.add_argument(
        "--discover-url-variants-only",
        action="store_true",
        help=(
            "When historical URL discovery is enabled, generate approved-candidate URL "
            "variants without fetching archived homepages."
        ),
    )
    parser.add_argument(
        "--require-url-variant-cdx-capture",
        action="store_true",
        help=(
            "When generating historical URL variants, first require a same-year successful "
            "HTML CDX capture before adding the variant to the candidate registry."
        ),
    )
    parser.add_argument("--historical-timeout-seconds", type=float, default=15.0)
    parser.add_argument("--historical-workers", type=int, default=4)
    parser.add_argument("--url-variant-probe-retries", type=int, default=3)
    parser.add_argument("--url-variant-probe-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--url-variant-probe-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--historical-candidates", type=Path, default=DEFAULT_HISTORICAL_CANDIDATES)
    parser.add_argument(
        "--historical-discovery-audit",
        type=Path,
        default=DEFAULT_HISTORICAL_DISCOVERY_AUDIT,
    )
    parser.add_argument(
        "--augmented-candidates",
        type=Path,
        default=DEFAULT_AUGMENTED_PAGE_CANDIDATES,
    )
    parser.add_argument(
        "--only-nonusable",
        action="store_true",
        help="Only run network discovery/fetch for current non-usable final rows.",
    )
    parser.add_argument(
        "--only-status",
        action="append",
        default=[],
        help=(
            "Only run network discovery/fetch for current final rows with this status; repeatable."
        ),
    )
    parser.add_argument("--progress-log", type=Path, default=DEFAULT_PROGRESS_LOG)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    args = parser.parse_args()

    summary = run_all(
        companies_path=args.companies,
        candidates_path=args.candidates,
        targets_path=args.targets,
        cache_dir=args.cache_dir,
        query_log_path=args.query_log,
        discovery_retries=args.discovery_retries,
        timeout_seconds=args.timeout_seconds,
        backoff_seconds=args.backoff_seconds,
        force_discovery=args.force_discovery,
        prefix_fallback=not args.no_prefix_fallback,
        replay_retries=args.replay_retries,
        workers=args.workers,
        fetch_timeout_seconds=args.fetch_timeout_seconds,
        fetch_retries=args.fetch_retries,
        fetch_backoff_seconds=args.fetch_backoff_seconds,
        force_fetch=args.force_fetch,
        only_nonusable=args.only_nonusable,
        only_statuses=parse_only_statuses(args.only_status),
        alternate_recovery_passes=args.alternate_recovery_passes,
        enable_trafilatura_fallback=args.enable_trafilatura_fallback,
        enable_wayback_json_api_fallback=args.enable_wayback_json_api_fallback,
        discover_historical_urls=args.discover_historical_urls,
        discover_url_variants_only=args.discover_url_variants_only,
        discover_domain_cdx_urls=args.discover_domain_cdx_urls,
        require_url_variant_cdx_capture=args.require_url_variant_cdx_capture,
        url_variant_probe_retries=args.url_variant_probe_retries,
        url_variant_probe_backoff_seconds=args.url_variant_probe_backoff_seconds,
        url_variant_probe_sleep_seconds=args.url_variant_probe_sleep_seconds,
        historical_timeout_seconds=args.historical_timeout_seconds,
        historical_workers=args.historical_workers,
        historical_candidates_path=args.historical_candidates,
        historical_discovery_audit_path=args.historical_discovery_audit,
        augmented_candidates_path=args.augmented_candidates,
        progress_log=args.progress_log,
        state_file=args.state_file,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
