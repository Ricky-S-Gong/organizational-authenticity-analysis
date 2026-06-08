import csv
import json
from pathlib import Path

from org_auth_part1 import llm_analysis
from org_auth_part1.llm_analysis import (
    annotation_quality,
    build_change_tasks,
    build_snapshot_tasks,
    clean_model_response,
    generate_responses,
    run_llm_analysis,
    value_relevant_excerpt,
)


def sample_rows() -> list[dict[str, str]]:
    return [
        {
            "ticker": "AAA",
            "company_name": "Alpha",
            "sector": "Technology",
            "year": "2020",
            "observation_status": "usable",
            "page_text_clean": "Our mission is to serve customers with integrity and innovation.",
            "clean_text_sha256": "hash-2020",
            "changed_from_prior": "",
            "change_magnitude": "",
        },
        {
            "ticker": "AAA",
            "company_name": "Alpha",
            "sector": "Technology",
            "year": "2021",
            "observation_status": "usable",
            "page_text_clean": (
                "Our mission is to serve customers with integrity, innovation, "
                "and community impact."
            ),
            "clean_text_sha256": "hash-2021",
            "changed_from_prior": "True",
            "change_magnitude": "minor_edit",
        },
        {
            "ticker": "BBB",
            "company_name": "Beta",
            "sector": "Energy",
            "year": "2020",
            "observation_status": "no_cdx_capture",
            "page_text_clean": "",
            "clean_text_sha256": "",
            "changed_from_prior": "",
            "change_magnitude": "",
        },
    ]


def write_final(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = sorted({field for row in rows for field in row})
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_value_relevant_excerpt_prefers_signal_terms() -> None:
    text = "Boilerplate. " * 100 + "Our mission is customer service and integrity."

    excerpt = value_relevant_excerpt(text, max_chars=120)

    assert "mission" in excerpt.lower()
    assert len(excerpt) <= 120


def test_build_tasks_skip_nonusable_and_prepare_adjacent_pairs() -> None:
    snapshot_rows, snapshot_prompts, snapshot_indexes = build_snapshot_tasks(
        sample_rows(), limit=None
    )
    change_rows, change_prompts, change_indexes = build_change_tasks(sample_rows(), limit=None)

    assert len(snapshot_prompts) == 2
    assert snapshot_indexes == [0, 1]
    assert snapshot_rows[2]["analysis_status"] == "skipped_nonusable"
    assert len(change_prompts) == 1
    assert change_indexes == [1]
    assert change_rows[0]["analysis_status"] == "skipped_no_prior"
    assert change_rows[1]["analysis_status"] == "pending"


def test_annotation_quality_flags_weak_responses() -> None:
    assert annotation_quality("yes") == "low_empty_or_fragment"
    assert annotation_quality("This is a free-form note.") == "medium_unstructured"
    assert annotation_quality("Themes: integrity\nTone: concise\nAnalyst note: cautious") == (
        "candidate_interpretive_signal"
    )


def test_clean_model_response_removes_thinking_blocks() -> None:
    response = "<think>\ninternal notes\n</think>\nThemes: integrity\nTone: concise"

    assert clean_model_response(response) == "Themes: integrity\nTone: concise"


def test_run_llm_analysis_writes_auditable_outputs(tmp_path: Path, monkeypatch) -> None:
    final = tmp_path / "part1_company_year.csv"
    output_dir = tmp_path / "llm"
    log = tmp_path / "run.jsonl"
    write_final(final, sample_rows())

    captured_generate_kwargs = {}

    def fake_generate(prompts: list[str], **kwargs: object) -> list[str]:
        captured_generate_kwargs.update(kwargs)
        return [
            "Themes: integrity, customers\nTone: purpose-driven\nAnalyst note: source-limited"
            for _prompt in prompts
        ]

    monkeypatch.setattr(llm_analysis, "generate_responses", fake_generate)
    manifest = run_llm_analysis(
        final_path=final,
        output_dir=output_dir,
        log_path=log,
        model_name="test-model",
        model_family="causal-chat",
        batch_size=2,
        local_files_only=True,
    )

    snapshot_rows = list(csv.DictReader((output_dir / "llm_snapshot_analysis.csv").open()))
    change_rows = list(csv.DictReader((output_dir / "llm_change_analysis.csv").open()))
    summary = json.loads((output_dir / "llm_analysis_summary.json").read_text())

    assert manifest["coverage"]["snapshot_status_counts"]["completed"] == 2
    assert manifest["coverage"]["change_status_counts"]["completed"] == 1
    assert manifest["model"]["model_family"] == "causal-chat"
    assert snapshot_rows[0]["model_name"] == "test-model"
    assert snapshot_rows[2]["analysis_status"] == "skipped_nonusable"
    assert change_rows[1]["analysis_status"] == "completed"
    assert summary["outputs"]["snapshot_analysis"].endswith("llm_snapshot_analysis.csv")
    assert summary["model"]["model_family"] == "causal-chat"
    assert captured_generate_kwargs["model_family"] == "causal-chat"
    assert log.exists()


def test_generate_responses_routes_model_families(monkeypatch) -> None:
    calls = []

    def fake_seq2seq(prompts: list[str], **kwargs: object) -> list[str]:
        calls.append(("seq2seq", kwargs))
        return ["seq2seq response" for _prompt in prompts]

    def fake_causal(prompts: list[str], **kwargs: object) -> list[str]:
        calls.append(("causal-chat", kwargs))
        return ["causal response" for _prompt in prompts]

    monkeypatch.setattr(llm_analysis, "generate_seq2seq_responses", fake_seq2seq)
    monkeypatch.setattr(llm_analysis, "generate_causal_chat_responses", fake_causal)

    seq2seq = generate_responses(
        ["prompt"],
        model_name="google/flan-t5-small",
        model_family="seq2seq",
        batch_size=4,
        max_input_tokens=128,
        max_new_tokens=32,
        local_files_only=True,
    )
    causal = generate_responses(
        ["prompt"],
        model_name="Qwen/Qwen3-4B-Instruct-2507",
        model_family="causal-chat",
        batch_size=4,
        max_input_tokens=128,
        max_new_tokens=32,
        local_files_only=False,
    )

    assert seq2seq == ["seq2seq response"]
    assert causal == ["causal response"]
    assert calls[0][0] == "seq2seq"
    assert calls[1][0] == "causal-chat"


def test_generate_responses_rejects_unknown_model_family() -> None:
    try:
        generate_responses(
            ["prompt"],
            model_name="model",
            model_family="unknown",
            batch_size=1,
            max_input_tokens=128,
            max_new_tokens=32,
            local_files_only=True,
        )
    except ValueError as error:
        assert "Unsupported model family" in str(error)
    else:
        raise AssertionError("Expected unsupported model family to raise ValueError")
