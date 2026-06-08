"""Validate generated Part 3 outputs against the research contract.

The validator is intentionally structural rather than inferential. It checks that the required
files, row counts, score fields, provenance fields, and status accounting are present so the final
dataset can be audited independently of the written narrative.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from org_auth_part3.constants import (
    AUDIT_OUTPUT,
    COMPANY_OUTPUT,
    DISTRIBUTION_OUTPUT,
    INDEX_OUTPUT,
    REQUIRED_INDEX_COLUMNS,
    SECTOR_OUTPUT,
    SEMANTIC_OUTPUT,
    SENSITIVITY_OUTPUT,
    TAXONOMY_VERSION,
    VALIDITY_OUTPUT,
    YEAR_OUTPUT,
)


def validate_outputs(index_path: Path = INDEX_OUTPUT) -> dict[str, object]:
    """Build a machine-readable Part 3 requirement audit."""

    index = pd.read_csv(index_path) if index_path.exists() else pd.DataFrame()
    columns = set(index.columns)
    scored = index[index.get("score_status", "") == "scored"] if not index.empty else index
    missing_columns = sorted(set(REQUIRED_INDEX_COLUMNS) - columns)
    duplicate_keys = []
    if not index.empty:
        duplicate_mask = index.duplicated(["ticker", "year"], keep=False)
        duplicate_keys = [
            f"{row.ticker}:{row.year}" for row in index[duplicate_mask].itertuples(index=False)
        ]
    # Each check maps to an explicit deliverable or scoring rule. Keeping the booleans separate
    # makes requirement_audit.json readable during review and easy to extend for Part 4.
    checks = {
        "index_exists": index_path.exists(),
        "expected_row_count": len(index) == 450,
        "unique_company_year_keys": len(index) == len(index.drop_duplicates(["ticker", "year"]))
        if not index.empty
        else False,
        "required_columns_present": not missing_columns,
        "scored_rows_have_scores": bool(
            len(scored)
            and scored[
                [
                    "authenticity_index",
                    "cosine_alignment",
                    "l1_alignment",
                    "jaccard_theme_overlap",
                    "sector_percentile",
                    "sector_z_score",
                ]
            ]
            .notna()
            .all()
            .all()
        ),
        "scored_rows_traceable": bool(
            len(scored)
            and scored[["part1_clean_text_sha256", "part2_clean_text_sha256"]]
            .notna()
            .all()
            .all()
        ),
        "scored_rows_have_semantic_status": bool(
            len(scored)
            and scored["semantic_similarity_status"].notna().all()
            and scored.loc[
                scored["semantic_similarity_status"] == "computed",
                "semantic_text_similarity",
            ]
            .notna()
            .all()
        ),
        "taxonomy_version_recorded": bool(
            len(index) and set(index["taxonomy_version"].dropna()) == {TAXONOMY_VERSION}
        ),
        "summary_outputs_exist": all(
            path.exists()
            for path in [
                DISTRIBUTION_OUTPUT,
                SECTOR_OUTPUT,
                YEAR_OUTPUT,
                COMPANY_OUTPUT,
                VALIDITY_OUTPUT,
                SENSITIVITY_OUTPUT,
                SEMANTIC_OUTPUT,
            ]
        ),
    }
    status_counts = (
        index["score_status"].value_counts().sort_index().to_dict()
        if "score_status" in index
        else {}
    )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "index_rows": len(index),
        "scored_rows": int(status_counts.get("scored", 0)),
        "score_status_counts": status_counts,
        "issues": {
            "missing_required_columns": missing_columns,
            "duplicate_company_year_keys": duplicate_keys,
        },
    }


def write_audit(
    index_path: Path = INDEX_OUTPUT,
    output_path: Path = AUDIT_OUTPUT,
) -> dict[str, object]:
    """Write and return the Part 3 requirement audit."""

    audit = validate_outputs(index_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX_OUTPUT)
    parser.add_argument("--output", type=Path, default=AUDIT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(write_audit(args.index, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
