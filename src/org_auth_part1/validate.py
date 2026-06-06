"""Validate Part 1 outputs against the take-home assessment requirements."""

import argparse
import csv
import json
from pathlib import Path

REQUIRED_FINAL_COLUMNS = {
    "ticker",
    "company_name",
    "sector",
    "year",
    "page_text_clean",
    "changed_from_prior",
    "theme_categories",
    "analyst_notes",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def audit_target_grid(path: Path) -> dict[str, object]:
    rows = read_rows(path)
    keys = {(row["ticker"], int(row["year"])) for row in rows}
    return {
        "passed": len(rows) == 450 and len(keys) == 450,
        "row_count": len(rows),
        "unique_company_years": len(keys),
    }


def audit_final_dataset(path: Path) -> dict[str, object]:
    rows = read_rows(path)
    columns = set(rows[0]) if rows else set()
    missing_columns = sorted(REQUIRED_FINAL_COLUMNS - columns)
    keys = {(row["ticker"], int(row["year"])) for row in rows}
    missing_gap_reasons = sum(
        1
        for row in rows
        if row.get("observation_status") != "usable" and not row.get("gap_reason")
    )
    return {
        "passed": (
            len(rows) == 450
            and len(keys) == 450
            and not missing_columns
            and missing_gap_reasons == 0
        ),
        "row_count": len(rows),
        "unique_company_years": len(keys),
        "missing_required_columns": missing_columns,
        "nonusable_without_gap_reason": missing_gap_reasons,
    }


def build_requirement_audit(
    target_grid: Path, final_dataset: Path | None = None
) -> dict[str, object]:
    audit: dict[str, object] = {
        "target_grid": audit_target_grid(target_grid),
        "final_dataset": {"passed": False, "reason": "not generated"},
    }
    if final_dataset and final_dataset.exists():
        audit["final_dataset"] = audit_final_dataset(final_dataset)
    audit["passed"] = all(
        section.get("passed", False)
        for section in audit.values()
        if isinstance(section, dict)
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-grid",
        type=Path,
        default=Path("part1_stated_values/data/processed/target_company_years.csv"),
    )
    parser.add_argument(
        "--final-dataset",
        type=Path,
        default=Path("part1_stated_values/outputs/part1_company_year.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("part1_stated_values/outputs/requirement_audit.json"),
    )
    args = parser.parse_args()
    audit = build_requirement_audit(args.target_grid, args.final_dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
