"""Validity and audit outputs for the Part 3 index.

The primary score is quantitative, but construct validity also needs face-validity review. This
module selects transparent high- and low-alignment cases with source URLs and theme summaries so a
human reader can inspect whether the score behaves plausibly.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from org_auth_part3.constants import INDEX_OUTPUT, VALIDITY_OUTPUT


def _load_json_list(value: Any) -> list[dict[str, Any]]:
    """Safely parse a serialized JSON list used in row-level theme diagnostics."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _theme_names(value: Any) -> str:
    """Format top-theme JSON evidence into a compact audit string."""

    return "; ".join(
        f"{item.get('theme_label')} ({item.get('match_count')})"
        for item in _load_json_list(value)
    )


def _gap_names(value: Any) -> str:
    """Format the largest stated-minus-disclosure gaps into a compact audit string."""

    rows = _load_json_list(value)
    return "; ".join(
        f"{item.get('theme_label')}: {item.get('stated_minus_disclosure')}" for item in rows[:3]
    )


def build_case_audit(index: pd.DataFrame, *, cases_per_tail: int = 10) -> pd.DataFrame:
    """Select high- and low-alignment company-years for face-validity review."""

    scored = index[index["score_status"] == "scored"].copy()
    # The high/low tails are not treated as ground truth. They are a targeted reading list for
    # checking whether the index's extreme values look sensible against source evidence.
    high = scored.sort_values(
        ["authenticity_index", "ticker", "year"],
        ascending=[False, True, True],
    )
    high = high.head(cases_per_tail).assign(audit_bucket="high_alignment")
    low = scored.sort_values(
        ["authenticity_index", "ticker", "year"],
        ascending=[True, True, True],
    )
    low = low.head(cases_per_tail).assign(audit_bucket="low_alignment")
    audit = pd.concat([high, low], ignore_index=True)
    return pd.DataFrame(
        {
            "audit_bucket": audit["audit_bucket"],
            "ticker": audit["ticker"],
            "company_name": audit["company_name"],
            "sector": audit["sector"],
            "year": audit["year"],
            "authenticity_index": audit["authenticity_index"],
            "cosine_alignment": audit["cosine_alignment"],
            "l1_alignment": audit["l1_alignment"],
            "jaccard_theme_overlap": audit["jaccard_theme_overlap"],
            "semantic_text_similarity": audit["semantic_text_similarity"],
            "stated_top_theme_summary": audit["stated_top_themes"].map(_theme_names),
            "disclosure_top_theme_summary": audit["disclosure_top_themes"].map(_theme_names),
            "largest_theme_gap_summary": audit["theme_gap_summary"].map(_gap_names),
            "part1_source_url": audit["part1_source_url"],
            "part2_sec_archive_url": audit["part2_sec_archive_url"],
        }
    )


def write_validity(
    index_path: Path = INDEX_OUTPUT,
    output_path: Path = VALIDITY_OUTPUT,
) -> pd.DataFrame:
    """Write the high/low case audit output."""

    index = pd.read_csv(index_path)
    audit = build_case_audit(index)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_path, index=False)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX_OUTPUT)
    parser.add_argument("--output", type=Path, default=VALIDITY_OUTPUT)
    args = parser.parse_args()
    audit = write_validity(args.index, args.output)
    print(json.dumps({"output": str(args.output), "rows": len(audit)}, indent=2))


if __name__ == "__main__":
    main()
