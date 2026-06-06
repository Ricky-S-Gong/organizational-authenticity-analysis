import csv
from pathlib import Path

from org_auth_part1.validate import audit_final_dataset, audit_target_grid


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_target_grid_audit_rejects_incomplete_grid(tmp_path: Path) -> None:
    path = tmp_path / "targets.csv"
    write_csv(path, ["ticker", "year"], [{"ticker": "MSFT", "year": 2024}])

    assert audit_target_grid(path)["passed"] is False


def test_final_dataset_audit_checks_required_columns_and_gap_reasons(tmp_path: Path) -> None:
    path = tmp_path / "final.csv"
    write_csv(
        path,
        [
            "ticker",
            "company_name",
            "sector",
            "year",
            "page_text_clean",
            "changed_from_prior",
            "theme_categories",
            "analyst_notes",
            "observation_status",
            "gap_reason",
        ],
        [
            {
                "ticker": "MSFT",
                "company_name": "Microsoft",
                "sector": "Technology",
                "year": 2024,
                "page_text_clean": "",
                "changed_from_prior": "",
                "theme_categories": "",
                "analyst_notes": "",
                "observation_status": "no_cdx_capture",
                "gap_reason": "",
            }
        ],
    )

    audit = audit_final_dataset(path)
    assert audit["passed"] is False
    assert audit["nonusable_without_gap_reason"] == 1
