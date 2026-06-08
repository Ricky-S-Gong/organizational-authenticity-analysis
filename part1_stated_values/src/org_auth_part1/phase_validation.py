"""Evaluate phase-specific Part 1 completion gates from generated artifacts."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV artifact, treating absent optional outputs as empty evidence."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def validate_phases(
    root: Path = Path("."), *, llm_analysis_completed: bool = False
) -> dict[str, Any]:
    """Evaluate the staged Part 1 completion gates from generated deliverables.

    These checks are intentionally conservative: they test structural completion and
    traceability, while substantive page quality and interpretation remain documented
    human-review responsibilities.
    """
    part = root / "part1_stated_values"
    targets = _rows(part / "data/processed/target_company_years.csv")
    candidates = _rows(part / "config/page_candidates.csv")
    statuses = _rows(part / "data/processed/acquisition_status.csv")
    artifacts = _rows(part / "data/processed/text_artifacts.csv")
    changes = _rows(part / "outputs/change_events.csv")
    themes = _rows(part / "outputs/theme_observations.csv")
    final = _rows(part / "outputs/part1_company_year.csv")
    review_decisions = _rows(part / "data/review/review_decisions.csv")
    llm_summary_exists = (part / "outputs/llm_analysis/llm_analysis_summary.json").exists()

    discovery_incomplete = sum(
        row.get("acquisition_status") == "discovery_incomplete" for row in statuses
    )
    target_tickers = {row.get("ticker") for row in targets}
    candidate_tickers = {row.get("ticker") for row in candidates}
    target_years = {row.get("year") for row in targets}
    sector_company_counts = {
        sector: len({row.get("ticker") for row in targets if row.get("sector") == sector})
        for sector in sorted({row.get("sector") for row in targets if row.get("sector")})
    }
    selected = sum(row.get("acquisition_status") == "selected" for row in statuses)
    usable = sum(row.get("observation_status") == "usable" for row in final)
    validation_report_exists = (part / "docs/validation_report.md").exists()
    completed_review_decisions = sum(
        row.get("review_status") == "completed" for row in review_decisions
    )
    phase_3_passed = len(statuses) == 450 and discovery_incomplete == 0
    phase_4_passed = (
        selected > 0
        and len(artifacts) == selected
        and usable > 0
        and len(review_decisions) == len(final) == 450
        and completed_review_decisions == len(review_decisions)
        and validation_report_exists
    )
    phase_5_passed = len(changes) == 450 and validation_report_exists
    phase_6_passed = bool(themes) and (llm_analysis_completed or llm_summary_exists)
    upstream_research_gates_passed = all(
        (phase_3_passed, phase_4_passed, phase_5_passed, phase_6_passed)
    )

    phase_results = {
        "phase_0_environment_and_contract": {
            "passed": (
                len(targets) == 450
                and len(target_tickers) == 50
                and target_years == {str(year) for year in range(2016, 2025)}
                and sorted(sector_company_counts.values()) == [10, 10, 10, 10, 10]
            ),
            "evidence": {
                "target_rows": len(targets),
                "companies": len(target_tickers),
                "years": sorted(target_years),
                "sector_company_counts": sector_company_counts,
            },
        },
        "phase_1_pilot_and_rule_lock": {
            "passed": (
                (part / "docs/methodology.md").exists()
                and validation_report_exists
                and len(candidates) >= 50
            ),
            "evidence": {
                "candidate_rows": len(candidates),
                "methodology_exists": (part / "docs/methodology.md").exists(),
                "validation_report_exists": validation_report_exists,
            },
        },
        "phase_2_candidate_registry": {
            "passed": target_tickers == candidate_tickers,
            "evidence": {
                "companies_with_candidates": len(candidate_tickers),
                "missing_company_candidates": sorted(target_tickers - candidate_tickers),
            },
        },
        "phase_3_cdx_and_snapshot_selection": {
            "passed": phase_3_passed,
            "evidence": {
                "status_rows": len(statuses),
                "discovery_incomplete_rows": discovery_incomplete,
            },
        },
        "phase_4_text_extraction": {
            "passed": phase_4_passed,
            "evidence": {
                "selected_rows": selected,
                "artifact_rows": len(artifacts),
                "usable_rows": usable,
                "review_decision_rows": len(review_decisions),
                "completed_review_decisions": completed_review_decisions,
                "validation_report_exists": validation_report_exists,
            },
        },
        "phase_5_change_detection": {
            "passed": phase_5_passed,
            "evidence": {
                "change_rows": len(changes),
                "validation_report_exists": validation_report_exists,
            },
        },
        "phase_6_theme_and_llm_analysis": {
            "passed": phase_6_passed,
            "evidence": {
                "theme_observation_rows": len(themes),
                "llm_analysis_completed": llm_analysis_completed or llm_summary_exists,
                "llm_summary_exists": llm_summary_exists,
                "validation_report_exists": validation_report_exists,
                "deterministic_baseline_completed": bool(themes),
            },
        },
        "phase_7_reporting_and_deliverables": {
            "passed": (
                len(final) == 450
                and (part / "docs/summary.md").exists()
                and upstream_research_gates_passed
            ),
            "evidence": {
                "final_rows": len(final),
                "summary_exists": (part / "docs/summary.md").exists(),
                "upstream_research_gates_passed": upstream_research_gates_passed,
            },
        },
    }
    return {
        "passed": all(result["passed"] for result in phase_results.values()),
        "phases": phase_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--llm-analysis-completed", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("part1_stated_values/outputs/phase_validation.json"),
    )
    args = parser.parse_args()
    result = validate_phases(args.root, llm_analysis_completed=args.llm_analysis_completed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
