"""Validate generated Part 2 outputs against the research contract."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from org_auth_part2.run import DEFAULT_AUDIT, DEFAULT_COVERAGE, DEFAULT_DATASET
from org_auth_part2.targets import PART2_ROOT

DEFAULT_ENHANCED_SUMMARY = (
    PART2_ROOT / "outputs/text_mining/enhanced/enhanced_text_mining_summary.json"
)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _enhanced_join_check(
    *,
    collected_rows: list[dict[str, str]],
    enhanced_summary: Path,
) -> dict[str, object]:
    if not enhanced_summary.exists():
        return {"exists": False}
    payload = json.loads(enhanced_summary.read_text(encoding="utf-8"))
    output_dir = Path(payload["output_dir"])
    required_fields = {"ticker", "year", "accession_number", "clean_text_sha256"}
    if any(not required_fields.issubset(row) for row in collected_rows):
        return {
            "exists": True,
            "summary": enhanced_summary.exists(),
            "schema_checkable": False,
            "reason": "Collected dataset lacks enhanced join-key fields.",
        }
    expected = {
        (row["ticker"], row["year"], row["accession_number"], row["clean_text_sha256"])
        for row in collected_rows
    }
    checks = {}
    for name, filename in {
        "document_topic_scores": "document_topic_scores.csv",
        "embedding_manifest": "embedding_manifest.csv",
        "spacy_features": "spacy_features.csv",
    }.items():
        rows = _read_csv_rows(output_dir / filename)
        observed = {
            (row["ticker"], row["year"], row["accession_number"], row["clean_text_sha256"])
            for row in rows
        }
        checks[name] = {
            "exists": (output_dir / filename).exists(),
            "row_count": len(rows),
            "joinable_to_collected_rows": bool(rows) and observed.issubset(expected),
            "covers_all_collected_rows": observed == expected if rows else False,
        }
    return {
        "exists": True,
        "summary": enhanced_summary.exists(),
        "collected_rows": payload.get("collected_rows"),
        "seed": payload.get("seed"),
        "dataset_sha256": payload.get("dataset_sha256"),
        "stage_statuses": {
            key: value.get("status") for key, value in payload.get("stage_results", {}).items()
        },
        "join_checks": checks,
    }


def validate_outputs(
    dataset: Path = DEFAULT_DATASET,
    coverage: Path = DEFAULT_COVERAGE,
    audit: Path = DEFAULT_AUDIT,
    enhanced_summary: Path = DEFAULT_ENHANCED_SUMMARY,
) -> dict[str, object]:
    csv.field_size_limit(sys.maxsize)
    rows = []
    if dataset.exists():
        with dataset.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    coverage_payload = json.loads(coverage.read_text(encoding="utf-8")) if coverage.exists() else {}
    audit_payload = json.loads(audit.read_text(encoding="utf-8")) if audit.exists() else {}
    collected_rows = [row for row in rows if row.get("collection_status") == "collected"]
    return {
        "dataset_exists": dataset.exists(),
        "coverage_exists": coverage.exists(),
        "audit_exists": audit.exists(),
        "row_count": len(rows),
        "collected_rows": len(collected_rows),
        "has_real_success_evidence": any(
            row.get("sec_archive_url")
            and row.get("raw_file_path")
            and int(row.get("raw_file_bytes") or 0) > 0
            and row.get("raw_content_sha256")
            and row.get("clean_text_sha256")
            and int(row.get("word_count") or 0) >= 1000
            for row in collected_rows
        ),
        "coverage": coverage_payload,
        "audit": audit_payload,
        "enhanced_text_mining": _enhanced_join_check(
            collected_rows=collected_rows,
            enhanced_summary=enhanced_summary,
        ),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate Part 2 generated outputs.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--enhanced-summary", type=Path, default=DEFAULT_ENHANCED_SUMMARY)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            validate_outputs(args.dataset, args.coverage, args.audit, args.enhanced_summary),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
