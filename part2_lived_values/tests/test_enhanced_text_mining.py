from __future__ import annotations

import csv
import json
from pathlib import Path

from org_auth_part2 import enhanced_text_mining as enhanced


def _doc(ticker: str, year: int, text: str) -> dict[str, object]:
    return {
        "doc_id": f"{ticker}-{year}",
        "ticker": ticker,
        "company_name": ticker,
        "sector": "Technology",
        "year": year,
        "accession_number": f"{ticker}-{year}-accession",
        "clean_text_sha256": enhanced.stable_hash(text),
        "source_url": "https://example.test",
        "word_count": len(text.split()),
        "text": text,
        "representative_text": enhanced.representative_text(text),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_representative_text_is_stable_front_window() -> None:
    text = "  alpha   beta\n" * 20
    assert enhanced.representative_text(text, max_chars=12) == "alpha beta a"


def test_llm_value_excerpt_prefers_value_signal_terms() -> None:
    text = "cover page boilerplate " * 80 + "Our employee culture prioritizes safety and ethics."
    excerpt = enhanced.llm_value_excerpt(text, max_chars=160)
    assert "employee culture" in excerpt
    assert "safety" in excerpt


def test_llm_annotation_quality_flags_fragments_and_signals() -> None:
    assert enhanced.llm_annotation_quality("") == "low_empty_or_fragment"
    assert enhanced.llm_annotation_quality("Board of Directors.") == "low_empty_or_fragment"
    assert (
        enhanced.llm_annotation_quality(
            "The excerpt links workforce safety investments to operational resilience."
        )
        == "candidate_interpretive_signal"
    )


def test_jsonl_logger_writes_auditable_records(tmp_path: Path) -> None:
    log_path = tmp_path / "run.jsonl"
    logger = enhanced.JsonlLogger(log_path)
    logger.event("unit", "started", seed=42)
    record = json.loads(log_path.read_text(encoding="utf-8"))
    assert record["stage"] == "unit"
    assert record["status"] == "started"
    assert record["seed"] == 42
    assert record["timestamp_utc"]


def test_tfidf_nmf_writes_joinable_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(enhanced, "TFIDF_MAX_FEATURES", 80)
    monkeypatch.setattr(enhanced, "TFIDF_MIN_DF", 1)
    monkeypatch.setattr(enhanced, "TFIDF_MAX_DF", 1.0)
    monkeypatch.setattr(enhanced, "NMF_COMPONENTS", 2)
    documents = [
        _doc("AAA", 2020, "governance board shareholder vote performance " * 8),
        _doc("AAA", 2021, "governance board shareholder vote performance " * 8),
        _doc("BBB", 2020, "employee diversity inclusion workplace culture " * 8),
        _doc("BBB", 2021, "employee diversity inclusion workplace culture " * 8),
        _doc("CCC", 2020, "climate sustainability emissions energy environment " * 8),
        _doc("CCC", 2021, "climate sustainability emissions energy environment " * 8),
    ]
    logger = enhanced.JsonlLogger(tmp_path / "log.jsonl")
    result = enhanced.tfidf_nmf_analysis(documents, tmp_path, seed=42, logger=logger)

    assert result["status"] == "completed"
    topics = _read_csv(tmp_path / "nmf_topics.csv")
    scores = _read_csv(tmp_path / "document_topic_scores.csv")
    assert len(topics) == 2
    assert len(scores) == len(documents)
    assert {row["doc_id"] for row in scores} == {doc["doc_id"] for doc in documents}
    assert all(row["clean_text_sha256"] for row in scores)


def test_build_manifest_records_versions_and_dataset_hash(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("ticker,year\nAAA,2020\n", encoding="utf-8")
    documents = [_doc("AAA", 2020, "governance board accountability")]
    manifest = enhanced.build_manifest(
        dataset=dataset,
        output_dir=tmp_path,
        log_path=tmp_path / "log.jsonl",
        seed=42,
        documents=documents,
        missing=[],
        stage_results={"tfidf_nmf": {"status": "completed"}},
    )
    assert manifest["dataset_sha256"] == enhanced.file_sha256(dataset)
    assert manifest["seed"] == 42
    assert manifest["package_versions"]["scikit-learn"] != "not_installed"
