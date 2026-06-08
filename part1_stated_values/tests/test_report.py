from org_auth_part1.report import audit_part1_requirements, coverage_summary


def record(ticker: str, year: int, status: str = "usable") -> dict[str, object]:
    usable = status == "usable"
    return {
        "ticker": ticker,
        "company_name": f"{ticker} Company",
        "sector": "Technology",
        "year": year,
        "observation_status": status,
        "gap_reason": None if usable else "no archived capture",
        "page_text_clean": "Our values include integrity." if usable else None,
        "changed_from_prior": False if usable else None,
        "theme_categories": ["integrity_and_ethics"] if usable else None,
        "theme_evidence": [{"theme_id": "integrity_and_ethics"}] if usable else None,
        "linguistic_shift_notes": "",
        "analyst_notes": "",
        "source_url": "https://web.archive.org/example" if usable else None,
        "capture_timestamp": "20200630120000" if usable else None,
    }


def test_coverage_summary_keeps_failure_statuses_distinct() -> None:
    summary = coverage_summary(
        [record("A", 2020), record("A", 2021, "no_cdx_capture"), record("B", 2020)]
    )

    assert summary["target_record_count"] == 3
    assert summary["usable_record_count"] == 2
    assert summary["status_counts"] == {"no_cdx_capture": 1, "usable": 2}


def test_requirement_audit_passes_complete_small_contract() -> None:
    records = [record(ticker, year) for ticker in ("A", "B") for year in (2020, 2021)]

    audit = audit_part1_requirements(
        records,
        expected_company_count=2,
        expected_years=(2020, 2021),
        llm_analysis_completed=True,
    )

    assert audit["passed"]
    assert all(audit["checks"].values())
    assert audit["human_review_required"]


def test_requirement_audit_accepts_string_years_and_blank_missing_change() -> None:
    row = record("A", 2016, "no_cdx_capture")
    row["year"] = "2016"
    row["changed_from_prior"] = ""

    audit = audit_part1_requirements(
        [row],
        expected_company_count=1,
        expected_years=(2016,),
        llm_analysis_completed=True,
    )

    assert audit["checks"]["years_within_scope"]
    assert audit["checks"]["missing_records_do_not_claim_no_change"]


def test_requirement_audit_finds_traceability_and_missing_semantics_failures() -> None:
    bad_usable = record("A", 2020)
    bad_usable["source_url"] = None
    bad_usable["theme_evidence"] = None
    bad_missing = record("B", 2020, "no_cdx_capture")
    bad_missing["gap_reason"] = None
    bad_missing["changed_from_prior"] = False

    audit = audit_part1_requirements(
        [bad_usable, bad_missing],
        expected_company_count=2,
        expected_years=(2020,),
        llm_analysis_completed=True,
    )

    assert not audit["passed"]
    assert audit["issues"]["untraceable_usable_records"] == ["A:2020"]
    assert audit["issues"]["themes_without_evidence"] == ["A:2020"]
    assert audit["issues"]["missing_failure_reasons"] == ["B:2020"]
    assert audit["issues"]["invalid_missing_change_values"] == ["B:2020"]


def test_requirement_audit_detects_duplicate_keys() -> None:
    audit = audit_part1_requirements(
        [record("A", 2020), record("A", 2020)],
        expected_company_count=1,
        expected_years=(2020,),
        llm_analysis_completed=True,
    )

    assert not audit["checks"]["unique_company_year_keys"]
    assert audit["issues"]["duplicate_company_year_keys"] == ["A:2020"]
