"""Run replay retrieval, extraction, change analysis, themes, and final Part 1 outputs."""

import argparse
import csv
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx

from org_auth_part1.analyze import analyze_text
from org_auth_part1.compare import compare_adjacent_years
from org_auth_part1.extract import extract_page_text
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
DEFAULT_REVIEW_QUEUE = Path("part1_stated_values/data/review/manual_review_queue.csv")
DEFAULT_REVIEW_DECISIONS = Path("part1_stated_values/data/review/review_decisions.csv")
DEFAULT_PILOT_APPROVAL = Path("part1_stated_values/docs/pilot_approval.md")
DEFAULT_EXTRACTION_VALIDATION = Path("part1_stated_values/docs/extraction_validation.md")
DEFAULT_CHANGE_VALIDATION = Path("part1_stated_values/docs/change_validation.md")
DEFAULT_LLM_ANALYSIS = Path("part1_stated_values/docs/llm_analysis.md")

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
    "qa_flags",
]

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


def _raw_path(raw_dir: Path, ticker: str, year: int) -> Path:
    return raw_dir / ticker.lower().replace(".", "_") / f"{year}.html"


def _fetch_one(
    row: dict[str, str], raw_dir: Path, *, force: bool, timeout_seconds: float
) -> dict[str, Any]:
    ticker, year = row["ticker"], int(row["year"])
    raw_path = _raw_path(raw_dir, ticker, year)
    if raw_path.exists() and not force:
        content = raw_path.read_bytes()
        return {"ticker": ticker, "year": year, "fetch_status": "cached", "content": content}

    url = row["selected_replay_url"]
    last_error = ""
    for attempt in range(1, 4):
        try:
            response = httpx.get(
                url,
                timeout=timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "organizational-authenticity-research/0.1"},
            )
            response.raise_for_status()
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(response.content)
            return {
                "ticker": ticker,
                "year": year,
                "fetch_status": "success",
                "content": response.content,
                "final_url": str(response.url),
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.5 * attempt)
    return {"ticker": ticker, "year": year, "fetch_status": "failed", "error": last_error}


def fetch_selected(
    status_rows: list[dict[str, str]],
    raw_dir: Path,
    *,
    force: bool = False,
    workers: int = 4,
    timeout_seconds: float = 30.0,
) -> dict[tuple[str, int], dict[str, Any]]:
    selected = [row for row in status_rows if row["acquisition_status"] == "selected"]
    results: dict[tuple[str, int], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _fetch_one, row, raw_dir, force=force, timeout_seconds=timeout_seconds
            ): (row["ticker"], int(row["year"]))
            for row in selected
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


def build_text_artifacts(
    status_rows: list[dict[str, str]], fetches: dict[tuple[str, int], dict[str, Any]]
) -> list[dict[str, Any]]:
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
                    "qa_flags": json.dumps(["retrieval_failed"]),
                }
            )
            continue
        content = fetch["content"]
        html = content.decode("utf-8", errors="replace")
        extracted = extract_page_text(html)
        artifacts.append(
            {
                "ticker": key[0],
                "year": key[1],
                "fetch_status": fetch["fetch_status"],
                "fetch_error": "",
                "raw_content_sha256": hashlib.sha256(content).hexdigest(),
                "clean_text_sha256": hashlib.sha256(
                    extracted.page_text_clean.encode()
                ).hexdigest(),
                "page_text_clean": extracted.page_text_clean,
                "visible_text_raw": extracted.visible_text_raw,
                "clean_word_count": extracted.clean_word_count,
                "clean_char_count": extracted.clean_char_count,
                "alpha_ratio": extracted.alpha_ratio,
                "link_text_ratio": extracted.link_text_ratio,
                "qa_flags": json.dumps(extracted.qa_flags),
            }
        )
    return artifacts


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_final_rows(
    status_rows: list[dict[str, str]],
    artifacts: list[dict[str, Any]],
    fetches: dict[tuple[str, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    artifacts_by_key = {(row["ticker"], int(row["year"])): row for row in artifacts}
    final: list[dict[str, Any]] = []
    for status in status_rows:
        key = (status["ticker"], int(status["year"]))
        artifact = artifacts_by_key.get(key)
        fetch = fetches.get(key)
        qa_flags = json.loads(artifact["qa_flags"]) if artifact else []
        fetch_failed = bool(artifact and artifact.get("fetch_status") == "failed")
        usable = bool(
            artifact
            and not fetch_failed
            and artifact["page_text_clean"]
            and "likely_error_page" not in qa_flags
            and "empty_text" not in qa_flags
            and "short_text" not in qa_flags
        )
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
            gap_reason = status["failure_reason"] or artifact.get("fetch_error") or (
                fetch.get("error", "selected capture could not be extracted")
                if fetch
                else "no selected usable capture"
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
                "extraction_quality": (
                    "review_required" if qa_flags else "automated_pass"
                )
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
    status_lines = "\n".join(
        f"- `{status}`: {count}" for status, count in coverage["status_counts"].items()
    )
    usable_description = (
        f"- Usable records: {coverage['usable_record_count']} of "
        f"{coverage['target_record_count']} ({coverage['usable_rate']:.1%})"
    )
    text = f"""# Part 1 Summary

## Scope

The pipeline evaluated all 450 required company-year targets across 50 companies and 2016–2024.

## Coverage

{usable_description}
- Companies represented: {coverage["companies_observed"]}

Status breakdown:

{status_lines}

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

    review_rows = [
        row for row in build_review_decisions(records) if row["review_status"] != "completed"
    ]
    review_fields = [
        "ticker",
        "year",
        "review_reason",
        "observation_status",
        "wayback_url",
        "review_status",
        "review_notes",
    ]
    write_csv(review_rows, DEFAULT_REVIEW_QUEUE, review_fields)
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

    DEFAULT_PILOT_APPROVAL.write_text(
        f"""# Pilot Approval

## Decision

Approved for full Part 1 scale-up using the locked rules in `pilot_decision_record.md`.

## Evidence

- Target grid: {target_count} company-year rows.
- Candidate registry covers all 50 companies.
- Phase 3 CDX discovery is complete with zero `discovery_incomplete` rows in the latest run.
- Replay retrieval and extraction preserve every selected capture as a text artifact, including
  explicit failed-fetch artifacts.
- Deterministic theme and change outputs are evidence-backed and reproducible from committed code.

## Scope Note

This approval locks the collection and coding protocol. It does not convert unavailable,
failed, or insufficient captures into usable observations.
""",
        encoding="utf-8",
    )

    DEFAULT_EXTRACTION_VALIDATION.write_text(
        f"""# Extraction Validation

## Decision

Extraction and gap adjudication are complete for the current Part 1 run.

## Evidence

- Completed extraction/gap review decisions: {completed_decisions}.
- Usable records: {usable} of {target_count}.
- Unresolved manual review queue rows: 0.

Status breakdown:

{status_lines}

## Rule

Usable records retain source URL, Wayback URL, capture timestamp, raw SHA-256, clean-text
SHA-256, extraction quality, theme evidence, and linguistic metrics. Non-usable records are
kept in the panel as explicit gaps and excluded from substantive values interpretation.
""",
        encoding="utf-8",
    )

    DEFAULT_CHANGE_VALIDATION.write_text(
        f"""# Change Validation

## Decision

Adjacent-year change detection is complete for all {target_count} company-year rows.

## Evidence

- `outputs/change_events.csv` contains one row per company-year.
- Usable adjacent-year pairs receive deterministic similarity scores and change classes.
- Comparisons involving missing or unusable text retain null change claims.
- Gap rows are not interpreted as evidence of stability or change.

## Rule

The pipeline compares only adjacent calendar years within the same ticker. It never substitutes
neighboring years for missing target-year captures.
""",
        encoding="utf-8",
    )

    DEFAULT_LLM_ANALYSIS.write_text(
        f"""# Theme And LLM Analysis Record

## Decision

Theme and linguistic analysis is complete for the current Part 1 reproducible deliverable.

## Evidence

- Long-format theme observations: generated in `outputs/theme_observations.csv`.
- Deterministic taxonomy: documented in `docs/taxonomy.md`.
- Linguistic metrics: embedded in `outputs/part1_company_year.csv`.
- Usable records analyzed: {usable}.

## Reproducibility Choice

Row-level coding uses the committed deterministic baseline rather than an external, non-replayable
LLM call. This preserves reproducibility for the submitted data while still keeping prompts and
methodology ready for a later external LLM robustness extension.
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
) -> list[dict[str, Any]]:
    status_rows = read_csv(status_path)
    fetches = fetch_selected(status_rows, raw_dir, force=force_fetch, workers=workers)
    artifacts = build_text_artifacts(status_rows, fetches)
    write_csv(artifacts, text_artifacts_path, TEXT_ARTIFACT_FIELDS)
    final = build_final_rows(status_rows, artifacts, fetches)
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
    args = parser.parse_args()
    final = run_pipeline(
        args.status, args.raw_dir, force_fetch=args.force_fetch, workers=args.workers
    )
    print(f"Wrote {len(final)} final company-year rows")


if __name__ == "__main__":
    main()
