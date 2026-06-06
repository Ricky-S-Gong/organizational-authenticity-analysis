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
