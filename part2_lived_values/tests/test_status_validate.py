import csv
import json
from pathlib import Path

from org_auth_part2.status import summarize
from org_auth_part2.validate import validate_outputs


def test_status_summarizes_progress_log(tmp_path: Path) -> None:
    progress = tmp_path / "progress.jsonl"
    state = tmp_path / "state.json"
    progress.write_text(
        '{"stage":"run","status":"started"}\n{"stage":"company_year","status":"collected","ticker":"AAPL"}\n',
        encoding="utf-8",
    )
    state.write_text('{"completed": 1, "total": 2}', encoding="utf-8")
    summary = summarize(progress, state)
    assert summary["event_counts"]["company_year:collected"] == 1
    assert summary["state"]["completed"] == 1


def test_validate_outputs_requires_real_success_evidence(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    coverage = tmp_path / "coverage.json"
    audit = tmp_path / "audit.json"
    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "collection_status",
                "sec_archive_url",
                "raw_file_path",
                "raw_file_bytes",
                "raw_content_sha256",
                "clean_text_sha256",
                "word_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "collection_status": "collected",
                "sec_archive_url": "https://www.sec.gov/example.htm",
                "raw_file_path": "part2_lived_values/data/raw/filings/example.htm",
                "raw_file_bytes": "20000",
                "raw_content_sha256": "a" * 64,
                "clean_text_sha256": "b" * 64,
                "word_count": "1500",
            }
        )
    coverage.write_text(json.dumps({"collected_rows": 1}), encoding="utf-8")
    audit.write_text(
        json.dumps({"successful_rows_have_source_hash_and_text_metrics": True}),
        encoding="utf-8",
    )
    result = validate_outputs(dataset, coverage, audit)
    assert result["has_real_success_evidence"] is True


def test_validate_outputs_checks_enhanced_joinability(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    coverage = tmp_path / "coverage.json"
    audit = tmp_path / "audit.json"
    enhanced_dir = tmp_path / "enhanced"
    enhanced_dir.mkdir()
    enhanced_summary = enhanced_dir / "enhanced_text_mining_summary.json"
    fieldnames = [
        "ticker",
        "year",
        "accession_number",
        "collection_status",
        "sec_archive_url",
        "raw_file_path",
        "raw_file_bytes",
        "raw_content_sha256",
        "clean_text_sha256",
        "word_count",
    ]
    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "ticker": "AAA",
                "year": "2020",
                "accession_number": "acc",
                "collection_status": "collected",
                "sec_archive_url": "https://www.sec.gov/example.htm",
                "raw_file_path": "part2_lived_values/data/raw/filings/example.htm",
                "raw_file_bytes": "20000",
                "raw_content_sha256": "a" * 64,
                "clean_text_sha256": "b" * 64,
                "word_count": "1500",
            }
        )
    for filename in ["document_topic_scores.csv", "embedding_manifest.csv", "spacy_features.csv"]:
        with (enhanced_dir / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["ticker", "year", "accession_number", "clean_text_sha256"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "ticker": "AAA",
                    "year": "2020",
                    "accession_number": "acc",
                    "clean_text_sha256": "b" * 64,
                }
            )
    enhanced_summary.write_text(
        json.dumps(
            {
                "output_dir": str(enhanced_dir),
                "collected_rows": 1,
                "seed": 42,
                "dataset_sha256": "hash",
                "stage_results": {"tfidf_nmf": {"status": "completed"}},
            }
        ),
        encoding="utf-8",
    )
    coverage.write_text(json.dumps({"collected_rows": 1}), encoding="utf-8")
    audit.write_text(json.dumps({}), encoding="utf-8")

    result = validate_outputs(dataset, coverage, audit, enhanced_summary)
    join_checks = result["enhanced_text_mining"]["join_checks"]
    assert join_checks["document_topic_scores"]["joinable_to_collected_rows"] is True
    assert join_checks["embedding_manifest"]["covers_all_collected_rows"] is True
