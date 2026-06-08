"""Auditable local-LLM analysis for Part 1 stated-values snapshots.

This stage keeps model-generated interpretation separate from the deterministic
baseline columns in ``part1_company_year.csv``. It uses local or explicitly
downloaded open-source models, records prompt/response hashes, and emits
explicit skip rows for non-usable observations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import random
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_FINAL = Path("part1_stated_values/outputs/part1_company_year.csv")
DEFAULT_OUTPUT_DIR = Path("part1_stated_values/outputs/llm_analysis")
DEFAULT_LOG = Path("part1_stated_values/data/interim/part1_llm_analysis_run_log.jsonl")

DEFAULT_MODEL = "Qwen/Qwen3-1.7B"
DEFAULT_MODEL_FAMILY = "causal-chat"
PROMPT_VERSION = "part1-local-llm-v1"
DEFAULT_SEED = 42
DEFAULT_MAX_INPUT_TOKENS = 768
DEFAULT_MAX_NEW_TOKENS = 80
DEFAULT_BATCH_SIZE = 8
MODEL_FAMILIES = ("seq2seq", "causal-chat")

SNAPSHOT_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "year",
    "observation_status",
    "analysis_status",
    "model_name",
    "prompt_version",
    "input_text_sha256",
    "prompt_sha256",
    "response_sha256",
    "input_excerpt",
    "llm_response",
    "annotation_quality_flag",
]

CHANGE_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "year",
    "prior_year",
    "analysis_status",
    "model_name",
    "prompt_version",
    "changed_from_prior_baseline",
    "change_magnitude_baseline",
    "prior_text_sha256",
    "current_text_sha256",
    "prompt_sha256",
    "response_sha256",
    "prior_excerpt",
    "current_excerpt",
    "llm_response",
    "annotation_quality_flag",
]

VALUE_SIGNAL_TERMS = (
    "mission",
    "purpose",
    "values",
    "vision",
    "customer",
    "customers",
    "employee",
    "employees",
    "people",
    "integrity",
    "ethics",
    "innovation",
    "quality",
    "sustainability",
    "community",
    "diversity",
    "inclusion",
    "safety",
    "shareholder",
    "leadership",
)

THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)


def utc_now() -> str:
    """Return a stable UTC timestamp for manifests and JSONL logs."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def stable_hash(text: str) -> str:
    """Hash exact text inputs, prompts, and model responses for audit replay."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def package_version(name: str) -> str:
    """Return an installed package version or a stable missing marker."""

    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not_installed"


def file_sha256(path: Path) -> str:
    """Hash an input or output file without loading large files all at once."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class JsonlLogger:
    """Append-only run logger for model stages and parameters."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, stage: str, status: str, **payload: Any) -> None:
        record = {
            "timestamp_utc": utc_now(),
            "stage": stage,
            "status": status,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")


def set_reproducible_seed(seed: int) -> None:
    """Seed Python and Torch when available; generation itself uses greedy decoding."""

    random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def preferred_torch_device() -> str:
    """Choose the best available local device without requiring extra packages."""

    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV with large text fields."""

    csv.field_size_limit(sys.maxsize)
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    """Write stable CSV outputs for model annotations."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a stable JSON manifest."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def compact_text(text: str) -> str:
    """Collapse whitespace while preserving source wording."""

    return " ".join(text.split())


def clean_model_response(response: str) -> str:
    """Remove hidden-reasoning wrappers while preserving the visible answer."""

    return THINK_BLOCK_RE.sub("", response).strip()


def value_relevant_excerpt(text: str, max_chars: int = 1800) -> str:
    """Select a deterministic excerpt likely to contain stated-values language."""

    compact = compact_text(text)
    lowered = compact.lower()
    windows: list[str] = []
    cursor = 0
    while len(" [...] ".join(windows)) < max_chars and cursor < len(compact):
        hits = [
            lowered.find(term, cursor)
            for term in VALUE_SIGNAL_TERMS
            if lowered.find(term, cursor) >= 0
        ]
        if not hits:
            break
        hit = min(hits)
        context_before = min(240, max_chars // 3)
        start = max(0, hit - context_before)
        end = min(len(compact), start + max_chars)
        snippet = compact[start:end].strip()
        if snippet and snippet not in windows:
            windows.append(snippet)
        cursor = hit + 1
    if windows:
        return " [...] ".join(windows)[:max_chars]
    return compact[:max_chars]


def snapshot_prompt(row: dict[str, str], excerpt: str) -> str:
    """Build the fixed prompt for one stated-values page snapshot."""

    return (
        "You are auditing a corporate stated-values page. "
        "Using only the excerpt, return concise notes in this exact format:\n"
        "Themes: <comma-separated value themes>\n"
        "Tone: <short description of language and emphasis>\n"
        "Analyst note: <one cautious sentence>\n\n"
        f"Company: {row['company_name']} ({row['ticker']})\n"
        f"Year: {row['year']}\n"
        f"Excerpt: {excerpt}"
    )


def change_prompt(
    current: dict[str, str],
    prior: dict[str, str],
    current_excerpt: str,
    prior_excerpt: str,
) -> str:
    """Build the fixed prompt for adjacent-year change analysis."""

    return (
        "You are comparing two adjacent annual versions of a corporate stated-values page. "
        "Using only these excerpts, return concise notes in this exact format:\n"
        "Changed: yes/no/unclear\n"
        "Main shift: <one sentence>\n"
        "Linguistic shift: <one sentence about tone, specificity, stakeholders, or evidence>\n\n"
        f"Company: {current['company_name']} ({current['ticker']})\n"
        f"Prior year {prior['year']} excerpt: {prior_excerpt}\n"
        f"Current year {current['year']} excerpt: {current_excerpt}"
    )


def annotation_quality(response: str) -> str:
    """Flag weak local-LLM responses for downstream caution."""

    cleaned = response.strip()
    lowered = cleaned.lower()
    if len(cleaned) < 20:
        return "low_empty_or_fragment"
    if lowered in {"yes", "no", "none", "n/a"}:
        return "low_uninformative"
    expected_terms = (
        "themes:",
        "tone:",
        "analyst note:",
        "changed:",
        "main shift:",
        "linguistic shift:",
    )
    if not any(term in lowered for term in expected_terms):
        return "medium_unstructured"
    return "candidate_interpretive_signal"


def batched(items: list[str], size: int) -> list[list[str]]:
    """Split prompts into deterministic batches."""

    return [items[index : index + size] for index in range(0, len(items), size)]


def generate_seq2seq_responses(
    prompts: list[str],
    *,
    model_name: str,
    batch_size: int,
    max_input_tokens: int,
    max_new_tokens: int,
    local_files_only: bool,
) -> list[str]:
    """Generate greedy responses from encoder-decoder instruction models."""

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, local_files_only=local_files_only)
    device = preferred_torch_device()
    model.to(device)
    model.eval()

    responses: list[str] = []
    with torch.no_grad():
        for prompt_batch in batched(prompts, batch_size):
            encoded = tokenizer(
                prompt_batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_input_tokens,
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            generated = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=max_new_tokens,
            )
            responses.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    return responses


def generate_causal_chat_responses(
    prompts: list[str],
    *,
    model_name: str,
    max_input_tokens: int,
    max_new_tokens: int,
    local_files_only: bool,
) -> list[str]:
    """Generate greedy responses from chat-tuned causal LMs such as Qwen Instruct.

    Causal chat models are run one prompt at a time to keep memory use predictable
    on laptops with unified memory. The prompts are still deterministic and
    auditable because sampling is disabled.
    """

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        local_files_only=local_files_only,
        torch_dtype="auto",
    )
    device = preferred_torch_device()
    model.to(device)
    model.eval()

    responses: list[str] = []
    system_message = (
        "You are a careful research assistant. Use only the supplied excerpt, "
        "stay concise, preserve uncertainty, and do not include hidden reasoning "
        "or <think> blocks. /no_think"
    )
    with torch.no_grad():
        for prompt in prompts:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ]
            try:
                encoded = tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                    truncation=True,
                    max_length=max_input_tokens,
                    enable_thinking=False,
                )
            except TypeError:
                encoded = tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                    truncation=True,
                    max_length=max_input_tokens,
                )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            generated = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
            prompt_token_count = encoded["input_ids"].shape[-1]
            response_tokens = generated[0][prompt_token_count:]
            decoded = tokenizer.decode(response_tokens, skip_special_tokens=True)
            responses.append(clean_model_response(decoded))
    return responses


def generate_responses(
    prompts: list[str],
    *,
    model_name: str,
    model_family: str,
    batch_size: int,
    max_input_tokens: int,
    max_new_tokens: int,
    local_files_only: bool,
) -> list[str]:
    """Route generation through the requested open-source model family."""

    if model_family == "seq2seq":
        return generate_seq2seq_responses(
            prompts,
            model_name=model_name,
            batch_size=batch_size,
            max_input_tokens=max_input_tokens,
            max_new_tokens=max_new_tokens,
            local_files_only=local_files_only,
        )
    if model_family == "causal-chat":
        return generate_causal_chat_responses(
            prompts,
            model_name=model_name,
            max_input_tokens=max_input_tokens,
            max_new_tokens=max_new_tokens,
            local_files_only=local_files_only,
        )
    msg = f"Unsupported model family: {model_family}. Expected one of {MODEL_FAMILIES}."
    raise ValueError(msg)


def build_snapshot_tasks(
    rows: list[dict[str, str]], *, limit: int | None
) -> tuple[list[dict[str, Any]], list[str], list[int]]:
    """Create snapshot output rows and collect prompt indexes needing generation."""

    output_rows: list[dict[str, Any]] = []
    prompts: list[str] = []
    prompt_indexes: list[int] = []
    generated = 0
    for row in rows:
        excerpt = value_relevant_excerpt(row.get("page_text_clean", ""))
        output = {
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "sector": row["sector"],
            "year": row["year"],
            "observation_status": row["observation_status"],
            "analysis_status": "skipped_nonusable",
            "model_name": "",
            "prompt_version": PROMPT_VERSION,
            "input_text_sha256": row.get("clean_text_sha256", ""),
            "prompt_sha256": "",
            "response_sha256": "",
            "input_excerpt": excerpt if row["observation_status"] == "usable" else "",
            "llm_response": "",
            "annotation_quality_flag": "not_applicable",
        }
        if row["observation_status"] == "usable" and (limit is None or generated < limit):
            prompt = snapshot_prompt(row, excerpt)
            output["analysis_status"] = "pending"
            output["prompt_sha256"] = stable_hash(prompt)
            prompts.append(prompt)
            prompt_indexes.append(len(output_rows))
            generated += 1
        output_rows.append(output)
    return output_rows, prompts, prompt_indexes


def build_change_tasks(
    rows: list[dict[str, str]], *, limit: int | None
) -> tuple[list[dict[str, Any]], list[str], list[int]]:
    """Create adjacent-year change rows and collect prompt indexes needing generation."""

    by_ticker: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], []).append(row)

    output_rows: list[dict[str, Any]] = []
    prompts: list[str] = []
    prompt_indexes: list[int] = []
    generated = 0
    for ticker in sorted(by_ticker):
        ticker_rows = sorted(by_ticker[ticker], key=lambda item: int(item["year"]))
        prior_by_year = {int(row["year"]): row for row in ticker_rows}
        for current in ticker_rows:
            year = int(current["year"])
            prior = prior_by_year.get(year - 1)
            analysis_status = "skipped_no_prior" if prior is None else "skipped_nonusable_pair"
            prior_excerpt = (
                value_relevant_excerpt(prior.get("page_text_clean", "")) if prior else ""
            )
            current_excerpt = value_relevant_excerpt(current.get("page_text_clean", ""))
            output = {
                "ticker": current["ticker"],
                "company_name": current["company_name"],
                "sector": current["sector"],
                "year": current["year"],
                "prior_year": prior["year"] if prior else "",
                "analysis_status": analysis_status,
                "model_name": "",
                "prompt_version": PROMPT_VERSION,
                "changed_from_prior_baseline": current.get("changed_from_prior", ""),
                "change_magnitude_baseline": current.get("change_magnitude", ""),
                "prior_text_sha256": prior.get("clean_text_sha256", "") if prior else "",
                "current_text_sha256": current.get("clean_text_sha256", ""),
                "prompt_sha256": "",
                "response_sha256": "",
                "prior_excerpt": prior_excerpt
                if prior and prior["observation_status"] == "usable"
                else "",
                "current_excerpt": (
                    current_excerpt if current["observation_status"] == "usable" else ""
                ),
                "llm_response": "",
                "annotation_quality_flag": "not_applicable",
            }
            if (
                prior
                and prior["observation_status"] == "usable"
                and current["observation_status"] == "usable"
                and (limit is None or generated < limit)
            ):
                prompt = change_prompt(current, prior, current_excerpt, prior_excerpt)
                output["analysis_status"] = "pending"
                output["prompt_sha256"] = stable_hash(prompt)
                prompts.append(prompt)
                prompt_indexes.append(len(output_rows))
                generated += 1
            output_rows.append(output)
    return output_rows, prompts, prompt_indexes


def fill_generated_rows(
    rows: list[dict[str, Any]],
    prompt_indexes: list[int],
    responses: list[str],
    *,
    model_name: str,
) -> None:
    """Attach generated responses and hashes to pending output rows in place."""

    for row_index, response in zip(prompt_indexes, responses, strict=True):
        response = clean_model_response(response)
        row = rows[row_index]
        row["analysis_status"] = "completed"
        row["model_name"] = model_name
        row["llm_response"] = response
        row["response_sha256"] = stable_hash(response)
        row["annotation_quality_flag"] = annotation_quality(response)


def run_llm_analysis(
    *,
    final_path: Path = DEFAULT_FINAL,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    log_path: Path = DEFAULT_LOG,
    model_name: str = DEFAULT_MODEL,
    model_family: str = DEFAULT_MODEL_FAMILY,
    seed: int = DEFAULT_SEED,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    limit: int | None = None,
    local_files_only: bool = True,
) -> dict[str, Any]:
    """Run snapshot and adjacent-change local LLM annotations."""

    if model_family not in MODEL_FAMILIES:
        msg = f"Unsupported model family: {model_family}. Expected one of {MODEL_FAMILIES}."
        raise ValueError(msg)

    started = time.monotonic()
    set_reproducible_seed(seed)
    logger = JsonlLogger(log_path)
    logger.event(
        "part1_llm_analysis",
        "started",
        final_path=str(final_path),
        output_dir=str(output_dir),
        model_name=model_name,
        model_family=model_family,
        seed=seed,
        batch_size=batch_size,
        max_input_tokens=max_input_tokens,
        max_new_tokens=max_new_tokens,
        limit=limit,
        local_files_only=local_files_only,
    )

    rows = read_csv(final_path)
    snapshot_rows, snapshot_prompts, snapshot_indexes = build_snapshot_tasks(rows, limit=limit)
    change_limit = None if limit is None else max(0, limit - len(snapshot_prompts))
    change_rows, change_prompts, change_indexes = build_change_tasks(rows, limit=change_limit)
    all_prompts = snapshot_prompts + change_prompts
    logger.event(
        "prompt_build",
        "completed",
        snapshot_prompts=len(snapshot_prompts),
        change_prompts=len(change_prompts),
        skipped_snapshot_rows=sum(
            row["analysis_status"].startswith("skipped") for row in snapshot_rows
        ),
        skipped_change_rows=sum(
            row["analysis_status"].startswith("skipped") for row in change_rows
        ),
    )

    responses = generate_responses(
        all_prompts,
        model_name=model_name,
        model_family=model_family,
        batch_size=batch_size,
        max_input_tokens=max_input_tokens,
        max_new_tokens=max_new_tokens,
        local_files_only=local_files_only,
    )
    snapshot_responses = responses[: len(snapshot_prompts)]
    change_responses = responses[len(snapshot_prompts) :]
    fill_generated_rows(
        snapshot_rows,
        snapshot_indexes,
        snapshot_responses,
        model_name=model_name,
    )
    fill_generated_rows(change_rows, change_indexes, change_responses, model_name=model_name)

    snapshot_path = output_dir / "llm_snapshot_analysis.csv"
    change_path = output_dir / "llm_change_analysis.csv"
    manifest_path = output_dir / "llm_analysis_summary.json"
    write_csv(snapshot_rows, snapshot_path, SNAPSHOT_FIELDS)
    write_csv(change_rows, change_path, CHANGE_FIELDS)

    manifest = {
        "run_completed_at_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "input": {
            "final_dataset": str(final_path),
            "final_dataset_sha256": file_sha256(final_path),
            "rows": len(rows),
            "usable_rows": sum(row["observation_status"] == "usable" for row in rows),
        },
        "model": {
            "model_name": model_name,
            "model_family": model_family,
            "local_files_only": local_files_only,
            "prompt_version": PROMPT_VERSION,
            "seed": seed,
            "batch_size": batch_size,
            "max_input_tokens": max_input_tokens,
            "max_new_tokens": max_new_tokens,
            "torch_device": preferred_torch_device(),
            "transformers_version": package_version("transformers"),
            "torch_version": package_version("torch"),
        },
        "outputs": {
            "snapshot_analysis": str(snapshot_path),
            "snapshot_analysis_sha256": file_sha256(snapshot_path),
            "change_analysis": str(change_path),
            "change_analysis_sha256": file_sha256(change_path),
            "run_log": str(log_path),
        },
        "coverage": {
            "snapshot_status_counts": dict(
                sorted(Counter(row["analysis_status"] for row in snapshot_rows).items())
            ),
            "snapshot_quality_counts": dict(
                sorted(Counter(row["annotation_quality_flag"] for row in snapshot_rows).items())
            ),
            "change_status_counts": dict(
                sorted(Counter(row["analysis_status"] for row in change_rows).items())
            ),
            "change_quality_counts": dict(
                sorted(Counter(row["annotation_quality_flag"] for row in change_rows).items())
            ),
        },
        "interpretation_policy": (
            "Local LLM annotations are an auditable exploratory layer. The deterministic "
            "theme/change baseline remains the primary structured dataset."
        ),
    }
    write_json(manifest_path, manifest)
    logger.event(
        "part1_llm_analysis",
        "completed",
        snapshot_rows=len(snapshot_rows),
        change_rows=len(change_rows),
        snapshot_completed=manifest["coverage"]["snapshot_status_counts"].get("completed", 0),
        change_completed=manifest["coverage"]["change_status_counts"].get("completed", 0),
        manifest=str(manifest_path),
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", type=Path, default=DEFAULT_FINAL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--model-family",
        choices=MODEL_FAMILIES,
        default=DEFAULT_MODEL_FAMILY,
        help="Use seq2seq for FLAN/T5-style models or causal-chat for Qwen/Llama-style chat LMs.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-input-tokens", type=int, default=DEFAULT_MAX_INPUT_TOKENS)
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow transformers to download the model if it is not already cached locally.",
    )
    args = parser.parse_args()

    manifest = run_llm_analysis(
        final_path=args.final,
        output_dir=args.output_dir,
        log_path=args.log,
        model_name=args.model,
        model_family=args.model_family,
        seed=args.seed,
        batch_size=args.batch_size,
        max_input_tokens=args.max_input_tokens,
        max_new_tokens=args.max_new_tokens,
        limit=args.limit,
        local_files_only=not args.allow_model_download,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
