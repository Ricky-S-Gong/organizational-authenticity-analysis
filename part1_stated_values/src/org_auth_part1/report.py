"""Coverage summaries and requirement audits for Part 1 deliverables."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

REQUIRED_YEARS = tuple(range(2016, 2025))
REQUIRED_FINAL_FIELDS = (
    "ticker",
    "company_name",
    "sector",
    "year",
    "observation_status",
    "page_text_clean",
    "changed_from_prior",
    "theme_categories",
    "linguistic_shift_notes",
    "analyst_notes",
    "source_url",
    "capture_timestamp",
)


def coverage_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize target coverage without treating missing records as value absence."""

    statuses = Counter(
        str(record.get("observation_status", "missing_status")) for record in records
    )
    usable = statuses.get("usable", 0)
    return {
        "target_record_count": len(records),
        "usable_record_count": usable,
        "usable_rate": round(usable / len(records), 4) if records else 0.0,
        "status_counts": dict(sorted(statuses.items())),
        "companies_observed": len(
            {record.get("ticker") for record in records if record.get("ticker")}
        ),
        "years_observed": sorted({record.get("year") for record in records if record.get("year")}),
    }


def _duplicate_keys(records: Sequence[Mapping[str, Any]]) -> list[str]:
    keys = Counter((record.get("ticker"), record.get("year")) for record in records)
    return [f"{ticker}:{year}" for (ticker, year), count in keys.items() if count > 1]


def _missing_failure_reasons(records: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        f"{record.get('ticker')}:{record.get('year')}"
        for record in records
        if record.get("observation_status") not in {"usable", "pending"}
        and not record.get("gap_reason")
    ]


def _untraceable_usable_records(records: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        f"{record.get('ticker')}:{record.get('year')}"
        for record in records
        if record.get("observation_status") == "usable"
        and (not record.get("source_url") or not record.get("capture_timestamp"))
    ]


def _themes_without_evidence(records: Sequence[Mapping[str, Any]]) -> list[str]:
    failures: list[str] = []
    for record in records:
        themes = record.get("theme_categories")
        evidence = record.get("theme_evidence")
        if themes and not evidence:
            failures.append(f"{record.get('ticker')}:{record.get('year')}")
    return failures


def audit_part1_requirements(
    records: Sequence[Mapping[str, Any]],
    *,
    expected_company_count: int = 50,
    expected_years: Sequence[int] = REQUIRED_YEARS,
    llm_analysis_completed: bool = False,
) -> dict[str, Any]:
    """Audit the required 50-company, 2016-2024 Part 1 output contract.

    This helper tests structural and traceability requirements. It cannot certify
    whether page selection, extraction quality, or interpretations are substantively correct;
    those remain human-review tasks.
    """

    expected_record_count = expected_company_count * len(expected_years)
    expected_year_strings = {str(year) for year in expected_years}
    actual_keys = {(record.get("ticker"), str(record.get("year"))) for record in records}
    companies = {record.get("ticker") for record in records if record.get("ticker")}
    missing_fields = sorted(
        {field for field in REQUIRED_FINAL_FIELDS if any(field not in record for record in records)}
    )
    duplicate_keys = _duplicate_keys(records)
    missing_failure_reasons = _missing_failure_reasons(records)
    untraceable_usable = _untraceable_usable_records(records)
    themes_without_evidence = _themes_without_evidence(records)
    years_outside_scope = sorted(
        {
            record.get("year")
            for record in records
            if str(record.get("year")) not in expected_year_strings
        },
        key=str,
    )
    invalid_missing_change = [
        f"{record.get('ticker')}:{record.get('year')}"
        for record in records
        if record.get("observation_status") != "usable"
        and record.get("changed_from_prior") not in {None, ""}
    ]
    discovery_incomplete = [
        f"{record.get('ticker')}:{record.get('year')}"
        for record in records
        if record.get("observation_status") == "discovery_incomplete"
    ]

    checks = {
        "expected_record_count": len(records) == expected_record_count,
        "unique_company_year_keys": len(actual_keys) == len(records) and not duplicate_keys,
        "expected_company_count": len(companies) == expected_company_count,
        "years_within_scope": not years_outside_scope,
        "required_fields_present": not missing_fields,
        "failures_have_reasons": not missing_failure_reasons,
        "usable_records_traceable": not untraceable_usable,
        "themes_have_evidence": not themes_without_evidence,
        "missing_records_do_not_claim_no_change": not invalid_missing_change,
        "discovery_queries_completed": not discovery_incomplete,
        "llm_analysis_completed": llm_analysis_completed,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "coverage": coverage_summary(records),
        "issues": {
            "duplicate_company_year_keys": duplicate_keys,
            "missing_required_fields": missing_fields,
            "missing_failure_reasons": missing_failure_reasons,
            "untraceable_usable_records": untraceable_usable,
            "themes_without_evidence": themes_without_evidence,
            "years_outside_scope": years_outside_scope,
            "invalid_missing_change_values": invalid_missing_change,
            "discovery_incomplete_records": discovery_incomplete,
            "llm_analysis_completed": llm_analysis_completed,
        },
        "human_review_required": [
            "Confirm selected pages represent official company-level stated values.",
            "Confirm extracted text preserves substantive content and removes boilerplate.",
            "Review all flagged changes and theme assignments against source evidence.",
            "Confirm final narrative claims are proportionate to coverage and limitations.",
        ],
    }
