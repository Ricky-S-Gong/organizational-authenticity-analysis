import csv
from pathlib import Path

from org_auth_part1.phase_validation import validate_phases


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_phase_validation_exposes_discovery_and_llm_failures(tmp_path: Path) -> None:
    part = tmp_path / "part1_stated_values"
    write_rows(
        part / "data/processed/acquisition_status.csv",
        ["ticker", "acquisition_status"],
        [{"ticker": "MSFT", "acquisition_status": "discovery_incomplete"}],
    )

    result = validate_phases(tmp_path)

    assert result["phases"]["phase_3_cdx_and_snapshot_selection"]["passed"] is False
    assert result["phases"]["phase_6_theme_and_llm_analysis"]["passed"] is False
    assert result["phases"]["phase_7_reporting_and_deliverables"]["passed"] is False


def test_phase_validation_requires_human_research_gates(tmp_path: Path) -> None:
    part = tmp_path / "part1_stated_values"
    for filename in (
        "methodology.md",
        "manual_review_protocol.md",
        "pilot_decision_record.md",
    ):
        path = part / "docs" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Test\n", encoding="utf-8")

    write_rows(
        part / "config/page_candidates.csv",
        ["ticker"],
        [{"ticker": f"C{i:02d}"} for i in range(50)],
    )

    result = validate_phases(tmp_path)

    assert result["phases"]["phase_1_pilot_and_rule_lock"]["passed"] is False
    assert (
        result["phases"]["phase_1_pilot_and_rule_lock"]["evidence"][
            "human_approval_recorded"
        ]
        is False
    )
    assert result["phases"]["phase_4_text_extraction"]["passed"] is False
    assert result["phases"]["phase_5_change_detection"]["passed"] is False


def test_phase_validation_passes_complete_research_gates(tmp_path: Path) -> None:
    part = tmp_path / "part1_stated_values"
    docs = part / "docs"
    for filename in (
        "methodology.md",
        "manual_review_protocol.md",
        "pilot_decision_record.md",
        "pilot_approval.md",
        "extraction_validation.md",
        "change_validation.md",
        "llm_analysis.md",
        "summary.md",
    ):
        path = docs / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Test\n", encoding="utf-8")

    targets = []
    for sector_index, sector in enumerate(("A", "B", "C", "D", "E")):
        for company_index in range(sector_index * 10, sector_index * 10 + 10):
            for year in range(2016, 2025):
                targets.append(
                    {
                        "ticker": f"C{company_index:02d}",
                        "company_name": f"Company {company_index:02d}",
                        "sector": sector,
                        "year": year,
                    }
                )
    write_rows(
        part / "data/processed/target_company_years.csv",
        ["ticker", "company_name", "sector", "year"],
        targets,
    )
    write_rows(
        part / "config/page_candidates.csv",
        ["ticker"],
        [{"ticker": f"C{i:02d}"} for i in range(50)],
    )
    write_rows(
        part / "data/processed/acquisition_status.csv",
        ["ticker", "year", "acquisition_status"],
        [
            {"ticker": row["ticker"], "year": row["year"], "acquisition_status": "selected"}
            for row in targets
        ],
    )
    write_rows(
        part / "data/processed/text_artifacts.csv",
        ["ticker", "year"],
        [{"ticker": row["ticker"], "year": row["year"]} for row in targets],
    )
    write_rows(
        part / "outputs/part1_company_year.csv",
        ["ticker", "year", "observation_status"],
        [
            {"ticker": row["ticker"], "year": row["year"], "observation_status": "usable"}
            for row in targets
        ],
    )
    write_rows(
        part / "data/review/manual_review_queue.csv",
        ["ticker", "year", "review_status"],
        [],
    )
    write_rows(
        part / "data/review/review_decisions.csv",
        ["ticker", "year", "review_status"],
        [
            {"ticker": row["ticker"], "year": row["year"], "review_status": "completed"}
            for row in targets
        ],
    )
    write_rows(
        part / "outputs/change_events.csv",
        ["ticker", "year"],
        [{"ticker": row["ticker"], "year": row["year"]} for row in targets],
    )
    write_rows(
        part / "outputs/theme_observations.csv",
        ["ticker", "year", "theme_id"],
        [{"ticker": "C00", "year": 2016, "theme_id": "purpose_and_identity"}],
    )

    result = validate_phases(tmp_path)

    assert result["passed"]
