"""Validate Part 4 outputs against the exploratory analysis contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from org_auth_part4.constants import (
    AUDIT_OUTPUT,
    CASE_AUDIT_OUTPUT,
    CODEBOOK_DOC,
    CORRELATION_OUTPUT,
    DIAGNOSTICS_OUTPUT,
    METHODOLOGY_DOC,
    QUADRANT_FIGURE,
    QUADRANT_OUTPUT,
    REGRESSION_OUTPUT,
    REQUIRED_DIAGNOSTIC_COLUMNS,
    REQUIRED_SECTION_COLUMNS,
    REQUIRED_THEME_SEMANTIC_COLUMNS,
    SCATTER_FIGURE,
    SECTION_COMPOSITION_FIGURE,
    SECTION_FIGURE,
    SECTION_OUTPUT,
    SECTION_SUMMARY_OUTPUT,
    SECTION_THEME_HEATMAP_FIGURE,
    SUMMARY_DOC,
    SUMMARY_OUTPUT,
    TERCILE_FIGURE,
    THEME_SEMANTIC_FIGURE,
    THEME_SEMANTIC_GAP_FIGURE,
    THEME_SEMANTIC_OUTPUT,
    THEME_SEMANTIC_SUMMARY_OUTPUT,
)


def validate_outputs(diagnostics_path: Path = DIAGNOSTICS_OUTPUT) -> dict[str, object]:
    """Return a machine-readable audit of Part 4 outputs."""

    diagnostics = pd.read_csv(diagnostics_path) if diagnostics_path.exists() else pd.DataFrame()
    sections = pd.read_csv(SECTION_OUTPUT) if SECTION_OUTPUT.exists() else pd.DataFrame()
    theme_semantic = (
        pd.read_csv(THEME_SEMANTIC_OUTPUT) if THEME_SEMANTIC_OUTPUT.exists() else pd.DataFrame()
    )
    columns = set(diagnostics.columns)
    section_columns = set(sections.columns)
    theme_semantic_columns = set(theme_semantic.columns)
    missing_columns = sorted(set(REQUIRED_DIAGNOSTIC_COLUMNS) - columns)
    missing_section_columns = sorted(set(REQUIRED_SECTION_COLUMNS) - section_columns)
    missing_theme_semantic_columns = sorted(
        set(REQUIRED_THEME_SEMANTIC_COLUMNS) - theme_semantic_columns
    )
    duplicate_keys = []
    if not diagnostics.empty:
        duplicate_mask = diagnostics.duplicated(["ticker", "year"], keep=False)
        duplicate_keys = [
            f"{row.ticker}:{row.year}"
            for row in diagnostics[duplicate_mask].itertuples(index=False)
        ]
    collected = (
        diagnostics[diagnostics["genre_status"] == "computed"]
        if "genre_status" in columns
        else diagnostics
    )
    scored = (
        diagnostics[diagnostics["score_status"] == "scored"]
        if "score_status" in columns
        else diagnostics
    )
    checks = {
        "diagnostics_exists": diagnostics_path.exists(),
        "expected_row_count": len(diagnostics) == 450,
        "unique_company_year_keys": len(diagnostics)
        == len(diagnostics.drop_duplicates(["ticker", "year"]))
        if not diagnostics.empty
        else False,
        "required_columns_present": not missing_columns,
        "computed_rows_have_genre_rates": bool(
            len(collected)
            and collected[
                [
                    "shareholder_mechanics_rate",
                    "governance_boilerplate_rate",
                    "legal_procedural_rate",
                    "proxy_genre_pressure",
                ]
            ]
            .notna()
            .all()
            .all()
        ),
        "scored_rows_retain_scores": bool(
            len(scored) and scored["authenticity_index"].notna().all()
        ),
        "analysis_outputs_exist": all(
            path.exists()
            for path in [
                SUMMARY_OUTPUT,
                CORRELATION_OUTPUT,
                QUADRANT_OUTPUT,
                CASE_AUDIT_OUTPUT,
                REGRESSION_OUTPUT,
                SECTION_OUTPUT,
                SECTION_SUMMARY_OUTPUT,
                THEME_SEMANTIC_OUTPUT,
                THEME_SEMANTIC_SUMMARY_OUTPUT,
            ]
        ),
        "figures_exist": all(
            path.exists()
            for path in [
                SCATTER_FIGURE,
                TERCILE_FIGURE,
                QUADRANT_FIGURE,
                SECTION_FIGURE,
                THEME_SEMANTIC_FIGURE,
                SECTION_THEME_HEATMAP_FIGURE,
                SECTION_COMPOSITION_FIGURE,
                THEME_SEMANTIC_GAP_FIGURE,
            ]
        ),
        "docs_exist": all(path.exists() for path in [SUMMARY_DOC, METHODOLOGY_DOC, CODEBOOK_DOC]),
        "section_outputs_valid": bool(
            len(sections)
            and not missing_section_columns
            and (sections["section_status"] == "parsed").any()
        ),
        "theme_semantic_outputs_valid": bool(
            len(theme_semantic) == 450 * 12
            and not missing_theme_semantic_columns
            and theme_semantic["theme_semantic_similarity"].notna().any()
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "diagnostic_rows": len(diagnostics),
        "computed_genre_rows": int((diagnostics.get("genre_status") == "computed").sum())
        if not diagnostics.empty
        else 0,
        "section_rows": len(sections),
        "theme_semantic_rows": len(theme_semantic),
        "scored_rows": int((diagnostics.get("score_status") == "scored").sum())
        if not diagnostics.empty
        else 0,
        "issues": {
            "missing_required_columns": missing_columns,
            "missing_section_columns": missing_section_columns,
            "missing_theme_semantic_columns": missing_theme_semantic_columns,
            "duplicate_company_year_keys": duplicate_keys,
        },
    }


def write_audit(output_path: Path = AUDIT_OUTPUT) -> dict[str, object]:
    """Write and return the Part 4 requirement audit."""

    audit = validate_outputs()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=AUDIT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(write_audit(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
