"""Enhanced, model-based Part 2 text mining.

This module keeps model-based interpretation separate from the deterministic
theme-matching baseline. Outputs are exploratory and auditable: every stage
records parameters, seed values, input hashes, and generated file paths.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from org_auth_part2.run import DEFAULT_DATASET
from org_auth_part2.targets import PART2_ROOT
from org_auth_part2.text_mining import write_csv

DEFAULT_OUTPUT_DIR = PART2_ROOT / "outputs/text_mining/enhanced"
DEFAULT_LOG = PART2_ROOT / "data/interim/enhanced_text_mining_run_log.jsonl"

DEFAULT_SEED = 42
TFIDF_MAX_FEATURES = 2500
TFIDF_MIN_DF = 5
TFIDF_MAX_DF = 0.85
NMF_COMPONENTS = 8
SENTENCE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPACY_MODEL = "en_core_web_sm"
LLM_MODEL = "google/flan-t5-small"
LLM_SIGNAL_TERMS = (
    "employee",
    "employees",
    "workforce",
    "culture",
    "diversity",
    "equity",
    "inclusion",
    "safety",
    "health",
    "climate",
    "sustainability",
    "emissions",
    "ethics",
    "integrity",
    "accountability",
    "customer",
    "customers",
    "community",
    "human capital",
    "shareholder engagement",
    "board oversight",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not_installed"


def dataset_sha256(path: Path) -> str:
    return file_sha256(path) if path.exists() else ""


class JsonlLogger:
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
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")


def set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def read_documents(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    csv.field_size_limit(sys.maxsize)
    documents: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["collection_status"] != "collected":
                missing.append(row)
                continue
            text = row.get("page_text_clean", "")
            documents.append(
                {
                    "doc_id": f"{row['ticker']}-{row['year']}",
                    "ticker": row["ticker"],
                    "company_name": row["company_name"],
                    "sector": row["sector"],
                    "year": int(row["year"]),
                    "accession_number": row["accession_number"],
                    "clean_text_sha256": row["clean_text_sha256"],
                    "source_url": row["source_url"],
                    "word_count": int(row["word_count"] or 0),
                    "text": text,
                    "representative_text": representative_text(text),
                }
            )
    return documents, missing


def representative_text(text: str, max_chars: int = 9000) -> str:
    """Return a stable front-window used by models with finite context windows."""
    compact = " ".join(text.split())
    return compact[:max_chars]


def llm_value_excerpt(text: str, max_chars: int = 1800) -> str:
    compact = " ".join(text.split())
    lowered = compact.lower()
    segments: list[str] = []
    cursor = 0
    while len(" ".join(segments)) < max_chars and cursor < len(compact):
        matches = [
            lowered.find(term, cursor)
            for term in LLM_SIGNAL_TERMS
            if lowered.find(term, cursor) >= 0
        ]
        if not matches:
            break
        hit = min(matches)
        context_before = min(220, max_chars // 3)
        context_after = max(500, max_chars - context_before)
        start = max(0, hit - context_before)
        end = min(len(compact), hit + context_after)
        snippet = compact[start:end].strip()
        if snippet and snippet not in segments:
            segments.append(snippet)
        cursor = hit + 1
    if segments:
        return " [...] ".join(segments)[:max_chars]
    fallback_start = min(2500, max(0, len(compact) // 4))
    return compact[fallback_start : fallback_start + max_chars]


def llm_annotation_quality(annotation: str) -> str:
    cleaned = annotation.strip()
    lower = cleaned.lower()
    if len(cleaned) < 20:
        return "low_empty_or_fragment"
    boilerplate_terms = (
        "united states securities and exchange commission",
        "schedule 14a",
        "proxy card",
        "no fee required",
        "board of directors",
        "appendix",
    )
    if any(term in lower for term in boilerplate_terms):
        return "low_boilerplate_like"
    return "candidate_interpretive_signal"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "status"}


def tfidf_nmf_analysis(
    documents: list[dict[str, Any]],
    output_dir: Path,
    seed: int,
    logger: JsonlLogger,
) -> dict[str, Any]:
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    stage = "tfidf_nmf"
    params = {
        "max_features": TFIDF_MAX_FEATURES,
        "min_df": TFIDF_MIN_DF,
        "max_df": TFIDF_MAX_DF,
        "ngram_range": [1, 2],
        "stop_words": "english",
        "sublinear_tf": True,
        "norm": "l2",
        "nmf_n_components": NMF_COMPONENTS,
        "nmf_init": "nndsvda",
        "nmf_solver": "cd",
        "nmf_max_iter": 400,
        "nmf_random_state": seed,
    }
    logger.event(stage, "started", document_count=len(documents), parameters=params)
    texts = [doc["representative_text"] for doc in documents]
    vectorizer = TfidfVectorizer(
        max_features=TFIDF_MAX_FEATURES,
        min_df=params["min_df"],
        max_df=params["max_df"],
        ngram_range=tuple(params["ngram_range"]),
        stop_words=params["stop_words"],
        sublinear_tf=params["sublinear_tf"],
        norm=params["norm"],
    )
    matrix = vectorizer.fit_transform(texts)
    model = NMF(
        n_components=NMF_COMPONENTS,
        init=params["nmf_init"],
        solver=params["nmf_solver"],
        max_iter=params["nmf_max_iter"],
        random_state=seed,
    )
    topic_scores = model.fit_transform(matrix)
    terms = vectorizer.get_feature_names_out()

    topic_rows: list[dict[str, Any]] = []
    term_rows: list[dict[str, Any]] = []
    for topic_idx, topic in enumerate(model.components_):
        ranked = sorted(
            ((terms[index], float(weight)) for index, weight in enumerate(topic)),
            key=lambda item: item[1],
            reverse=True,
        )
        top_terms = ranked[:12]
        topic_label = " / ".join(term for term, _ in top_terms[:4])
        topic_rows.append(
            {
                "topic_id": f"nmf_topic_{topic_idx + 1}",
                "topic_label": topic_label,
                "top_terms": "; ".join(term for term, _ in top_terms),
                "reconstruction_error": round(float(model.reconstruction_err_), 6),
                "n_iter": int(model.n_iter_),
            }
        )
        for rank, (term, weight) in enumerate(top_terms, start=1):
            term_rows.append(
                {
                    "topic_id": f"nmf_topic_{topic_idx + 1}",
                    "rank": rank,
                    "term": term,
                    "weight": round(weight, 8),
                }
            )

    score_rows: list[dict[str, Any]] = []
    topic_totals = topic_scores.sum(axis=0)
    for doc, scores in zip(documents, topic_scores, strict=False):
        dominant_index = int(scores.argmax())
        score_rows.append(
            {
                "doc_id": doc["doc_id"],
                "ticker": doc["ticker"],
                "company_name": doc["company_name"],
                "sector": doc["sector"],
                "year": doc["year"],
                "accession_number": doc["accession_number"],
                "clean_text_sha256": doc["clean_text_sha256"],
                "dominant_topic_id": f"nmf_topic_{dominant_index + 1}",
                "dominant_topic_score": round(float(scores[dominant_index]), 8),
                **{
                    f"nmf_topic_{index + 1}_score": round(float(score), 8)
                    for index, score in enumerate(scores)
                },
            }
        )

    sector_rows = summarize_topic_scores_by_group(
        documents,
        topic_scores,
        [row["topic_id"] for row in topic_rows],
        "sector",
    )
    year_rows = summarize_topic_scores_by_group(
        documents,
        topic_scores,
        [row["topic_id"] for row in topic_rows],
        "year",
    )

    write_csv(output_dir / "nmf_topics.csv", topic_rows)
    write_csv(output_dir / "tfidf_topic_terms.csv", term_rows)
    write_csv(output_dir / "document_topic_scores.csv", score_rows)
    write_csv(output_dir / "topic_sector_summary.csv", sector_rows)
    write_csv(output_dir / "topic_year_summary.csv", year_rows)

    result = {
        "status": "completed",
        "parameters": params,
        "document_count": len(documents),
        "vocabulary_size": len(terms),
        "n_topics": NMF_COMPONENTS,
        "reconstruction_error": round(float(model.reconstruction_err_), 6),
        "n_iter": int(model.n_iter_),
        "dominant_corpus_topics": [
            {
                "topic_id": f"nmf_topic_{index + 1}",
                "total_score": round(float(score), 6),
                "topic_label": topic_rows[index]["topic_label"],
            }
            for index, score in sorted(
                enumerate(topic_totals),
                key=lambda item: float(item[1]),
                reverse=True,
            )
        ],
        "files": {
            "nmf_topics": str(output_dir / "nmf_topics.csv"),
            "tfidf_topic_terms": str(output_dir / "tfidf_topic_terms.csv"),
            "document_topic_scores": str(output_dir / "document_topic_scores.csv"),
            "topic_sector_summary": str(output_dir / "topic_sector_summary.csv"),
            "topic_year_summary": str(output_dir / "topic_year_summary.csv"),
        },
    }
    logger.event(stage, "completed", **log_payload(result))
    return result


def summarize_topic_scores_by_group(
    documents: list[dict[str, Any]],
    topic_scores: Any,
    topic_ids: list[str],
    group_field: str,
) -> list[dict[str, Any]]:
    grouped: dict[Any, list[int]] = defaultdict(list)
    for index, doc in enumerate(documents):
        grouped[doc[group_field]].append(index)
    output: list[dict[str, Any]] = []
    for group, indexes in sorted(grouped.items(), key=lambda item: str(item[0])):
        for topic_idx, topic_id in enumerate(topic_ids):
            values = [float(topic_scores[index][topic_idx]) for index in indexes]
            output.append(
                {
                    group_field: group,
                    "topic_id": topic_id,
                    "document_count": len(indexes),
                    "mean_topic_score": round(sum(values) / len(values), 8),
                    "total_topic_score": round(sum(values), 8),
                }
            )
    return output


def embedding_analysis(
    documents: list[dict[str, Any]],
    output_dir: Path,
    seed: int,
    logger: JsonlLogger,
    model_name: str = SENTENCE_MODEL,
) -> dict[str, Any]:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    stage = "sentence_embeddings"
    params = {
        "model_name": model_name,
        "normalize_embeddings": True,
        "representative_text_max_chars": 9000,
        "batch_size": 16,
        "seed": seed,
    }
    logger.event(stage, "started", document_count=len(documents), parameters=params)
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        [doc["representative_text"] for doc in documents],
        batch_size=params["batch_size"],
        normalize_embeddings=params["normalize_embeddings"],
        show_progress_bar=False,
    )
    embedding_path = output_dir / "document_embeddings.npy"
    np.save(embedding_path, embeddings)
    embedding_hash = file_sha256(embedding_path)

    manifest_rows = []
    for doc, vector in zip(documents, embeddings, strict=False):
        manifest_rows.append(
            {
                "doc_id": doc["doc_id"],
                "ticker": doc["ticker"],
                "company_name": doc["company_name"],
                "sector": doc["sector"],
                "year": doc["year"],
                "accession_number": doc["accession_number"],
                "clean_text_sha256": doc["clean_text_sha256"],
                "model_name": model_name,
                "embedding_dim": int(len(vector)),
                "normalize_embeddings": params["normalize_embeddings"],
                "representative_text_sha256": stable_hash(doc["representative_text"]),
                "embedding_file": str(embedding_path),
                "embedding_file_sha256": embedding_hash,
            }
        )
    write_csv(output_dir / "embedding_manifest.csv", manifest_rows)

    similarities = cosine_similarity(embeddings)
    pair_rows: list[dict[str, Any]] = []
    n = len(documents)
    for i in range(n):
        for j in range(i + 1, n):
            same_ticker = documents[i]["ticker"] == documents[j]["ticker"]
            same_sector = documents[i]["sector"] == documents[j]["sector"]
            if same_ticker or same_sector:
                pair_rows.append(
                    {
                        "doc_id_a": documents[i]["doc_id"],
                        "doc_id_b": documents[j]["doc_id"],
                        "ticker_a": documents[i]["ticker"],
                        "ticker_b": documents[j]["ticker"],
                        "year_a": documents[i]["year"],
                        "year_b": documents[j]["year"],
                        "sector_a": documents[i]["sector"],
                        "sector_b": documents[j]["sector"],
                        "same_ticker": same_ticker,
                        "same_sector": same_sector,
                        "cosine_similarity": round(float(similarities[i, j]), 8),
                    }
                )
    pair_rows.sort(key=lambda row: row["cosine_similarity"], reverse=True)
    write_csv(output_dir / "embedding_similarity_top_pairs.csv", pair_rows[:500])

    adjacent_rows: list[dict[str, Any]] = []
    by_ticker: dict[str, list[int]] = defaultdict(list)
    for index, doc in enumerate(documents):
        by_ticker[doc["ticker"]].append(index)
    for ticker, indexes in by_ticker.items():
        ordered = sorted(indexes, key=lambda idx: documents[idx]["year"])
        for prior, current in zip(ordered, ordered[1:], strict=False):
            adjacent_rows.append(
                {
                    "ticker": ticker,
                    "company_name": documents[current]["company_name"],
                    "sector": documents[current]["sector"],
                    "prior_year": documents[prior]["year"],
                    "year": documents[current]["year"],
                    "doc_id_prior": documents[prior]["doc_id"],
                    "doc_id_current": documents[current]["doc_id"],
                    "cosine_similarity": round(float(similarities[prior, current]), 8),
                    "semantic_distance": round(1 - float(similarities[prior, current]), 8),
                }
            )
    adjacent_rows.sort(key=lambda row: row["semantic_distance"], reverse=True)
    write_csv(output_dir / "embedding_adjacent_year_shifts.csv", adjacent_rows)

    result = {
        "status": "completed",
        "parameters": params,
        "document_count": len(documents),
        "embedding_dim": int(embeddings.shape[1]),
        "embedding_file_sha256": embedding_hash,
        "max_adjacent_semantic_shift": adjacent_rows[0] if adjacent_rows else {},
        "files": {
            "embedding_manifest": str(output_dir / "embedding_manifest.csv"),
            "embedding_similarity_top_pairs": str(
                output_dir / "embedding_similarity_top_pairs.csv"
            ),
            "embedding_adjacent_year_shifts": str(
                output_dir / "embedding_adjacent_year_shifts.csv"
            ),
            "document_embeddings": str(embedding_path),
        },
    }
    logger.event(stage, "completed", **log_payload(result))
    return result


def spacy_analysis(
    documents: list[dict[str, Any]],
    output_dir: Path,
    logger: JsonlLogger,
    model_name: str = SPACY_MODEL,
) -> dict[str, Any]:
    import spacy

    stage = "spacy_pipeline"
    params = {
        "model_name": model_name,
        "representative_text_max_chars": 9000,
        "components": ["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer", "ner"],
    }
    logger.event(stage, "started", document_count=len(documents), parameters=params)
    nlp = spacy.load(model_name)
    nlp.max_length = max(nlp.max_length, 2_000_000)
    rows: list[dict[str, Any]] = []
    entity_counter: Counter[str] = Counter()
    for doc_record in documents:
        parsed = nlp(doc_record["representative_text"])
        tokens = [token for token in parsed if not token.is_space]
        pos_counts = Counter(token.pos_ for token in tokens)
        entity_counts = Counter(entity.label_ for entity in parsed.ents)
        entity_counter.update(
            entity.text.strip() for entity in parsed.ents if entity.label_ == "ORG"
        )
        token_count = len(tokens) or 1
        rows.append(
            {
                "doc_id": doc_record["doc_id"],
                "ticker": doc_record["ticker"],
                "company_name": doc_record["company_name"],
                "sector": doc_record["sector"],
                "year": doc_record["year"],
                "accession_number": doc_record["accession_number"],
                "clean_text_sha256": doc_record["clean_text_sha256"],
                "spacy_model": model_name,
                "spacy_model_version": package_version(model_name.replace("_", "-")),
                "representative_text_sha256": stable_hash(doc_record["representative_text"]),
                "token_count": token_count,
                "sentence_count": len(list(parsed.sents)),
                "entity_count": len(parsed.ents),
                "org_entity_count": entity_counts.get("ORG", 0),
                "person_entity_count": entity_counts.get("PERSON", 0),
                "money_entity_count": entity_counts.get("MONEY", 0),
                "percent_entity_count": entity_counts.get("PERCENT", 0),
                "noun_rate": round(pos_counts.get("NOUN", 0) / token_count, 8),
                "verb_rate": round(pos_counts.get("VERB", 0) / token_count, 8),
                "proper_noun_rate": round(pos_counts.get("PROPN", 0) / token_count, 8),
                "modal_count": sum(1 for token in tokens if token.tag_ == "MD"),
            }
        )
    write_csv(output_dir / "spacy_features.csv", rows)
    top_orgs = [
        {"entity_text": entity, "count": count}
        for entity, count in entity_counter.most_common(100)
    ]
    write_csv(output_dir / "spacy_top_org_entities.csv", top_orgs)
    result = {
        "status": "completed",
        "parameters": params,
        "document_count": len(documents),
        "spacy_version": package_version("spacy"),
        "spacy_model_version": package_version(model_name.replace("_", "-")),
        "files": {
            "spacy_features": str(output_dir / "spacy_features.csv"),
            "spacy_top_org_entities": str(output_dir / "spacy_top_org_entities.csv"),
        },
    }
    logger.event(stage, "completed", **log_payload(result))
    return result


def llm_annotation_analysis(
    documents: list[dict[str, Any]],
    output_dir: Path,
    seed: int,
    logger: JsonlLogger,
    model_name: str = LLM_MODEL,
    sample_size: int = 8,
    temperature: float = 0.1,
) -> dict[str, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, set_seed

    stage = "local_llm_annotations"
    params = {
        "model_name": model_name,
        "sample_size": sample_size,
        "seed": seed,
        "temperature": temperature,
        "do_sample": True,
        "max_new_tokens": 90,
        "prompt_version": "part2-enhanced-llm-v1",
        "input_selection": "largest documents by word_count, value-term excerpt windows",
    }
    logger.event(stage, "started", document_count=len(documents), parameters=params)
    set_seed(seed)
    selected = sorted(documents, key=lambda row: row["word_count"], reverse=True)[:sample_size]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    rows: list[dict[str, Any]] = []
    prompt_template = (
        "Read this SEC proxy excerpt and identify the main disclosed lived-value signal. "
        "Do not invent facts. Return one concise sentence.\n\nExcerpt:\n{text}\n\nAnswer:"
    )
    for doc in selected:
        excerpt = llm_value_excerpt(doc["text"])
        prompt = prompt_template.format(text=excerpt)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        generated = model.generate(
            **inputs,
            do_sample=params["do_sample"],
            temperature=temperature,
            max_new_tokens=params["max_new_tokens"],
        )
        response = tokenizer.decode(generated[0], skip_special_tokens=True).strip()
        rows.append(
            {
                "doc_id": doc["doc_id"],
                "ticker": doc["ticker"],
                "company_name": doc["company_name"],
                "sector": doc["sector"],
                "year": doc["year"],
                "accession_number": doc["accession_number"],
                "clean_text_sha256": doc["clean_text_sha256"],
                "model_name": model_name,
                "prompt_version": params["prompt_version"],
                "seed": seed,
                "temperature": temperature,
                "prompt_sha256": stable_hash(prompt),
                "excerpt_sha256": stable_hash(excerpt),
                "response_sha256": stable_hash(response),
                "annotation": response,
                "annotation_quality_flag": llm_annotation_quality(response),
                "review_status": "needs_human_review",
            }
        )
    write_csv(output_dir / "llm_annotations.csv", rows)
    result = {
        "status": "completed",
        "parameters": params,
        "document_count": len(selected),
        "files": {"llm_annotations": str(output_dir / "llm_annotations.csv")},
    }
    logger.event(stage, "completed", **log_payload(result))
    return result


def stage_error_result(stage: str, error: Exception, logger: JsonlLogger) -> dict[str, Any]:
    result = {
        "status": "failed",
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    logger.event(stage, "failed", **log_payload(result))
    return result


def build_manifest(
    dataset: Path,
    output_dir: Path,
    log_path: Path,
    seed: int,
    documents: list[dict[str, Any]],
    missing: list[dict[str, str]],
    stage_results: dict[str, Any],
) -> dict[str, Any]:
    return {
        "method": (
            "Enhanced exploratory text mining using free/open-source models; "
            "kept separate from deterministic phrase-evidence baseline."
        ),
        "created_at_utc": utc_now(),
        "dataset": str(dataset),
        "dataset_sha256": dataset_sha256(dataset),
        "output_dir": str(output_dir),
        "log_path": str(log_path),
        "seed": seed,
        "collected_rows": len(documents),
        "missing_rows": len(missing),
        "python": sys.version,
        "platform": platform.platform(),
        "package_versions": {
            "scikit-learn": package_version("scikit-learn"),
            "sentence-transformers": package_version("sentence-transformers"),
            "spacy": package_version("spacy"),
            "en-core-web-sm": package_version("en-core-web-sm"),
            "transformers": package_version("transformers"),
            "torch": package_version("torch"),
        },
        "stage_results": stage_results,
    }


def run_enhanced_text_mining(
    dataset: Path,
    output_dir: Path,
    log_path: Path,
    seed: int = DEFAULT_SEED,
    enable_llm: bool = False,
    continue_on_model_error: bool = True,
) -> dict[str, Any]:
    start = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = JsonlLogger(log_path)
    set_reproducible_seed(seed)
    logger.event(
        "enhanced_text_mining",
        "started",
        dataset=str(dataset),
        output_dir=str(output_dir),
        seed=seed,
        enable_llm=enable_llm,
    )
    documents, missing = read_documents(dataset)
    stage_results: dict[str, Any] = {}

    for stage_name, func in [
        ("tfidf_nmf", lambda: tfidf_nmf_analysis(documents, output_dir, seed, logger)),
        ("sentence_embeddings", lambda: embedding_analysis(documents, output_dir, seed, logger)),
        ("spacy_pipeline", lambda: spacy_analysis(documents, output_dir, logger)),
    ]:
        try:
            stage_results[stage_name] = func()
        except Exception as error:
            stage_results[stage_name] = stage_error_result(stage_name, error, logger)
            if not continue_on_model_error:
                raise

    if enable_llm:
        try:
            stage_results["local_llm_annotations"] = llm_annotation_analysis(
                documents,
                output_dir,
                seed,
                logger,
            )
        except Exception as error:
            stage_results["local_llm_annotations"] = stage_error_result(
                "local_llm_annotations",
                error,
                logger,
            )
            if not continue_on_model_error:
                raise
    else:
        stage_results["local_llm_annotations"] = {
            "status": "skipped",
            "reason": "Run with --enable-llm to generate sampled local LLM annotations.",
        }
        logger.event(
            "local_llm_annotations",
            "skipped",
            **log_payload(stage_results["local_llm_annotations"]),
        )

    manifest = build_manifest(
        dataset=dataset,
        output_dir=output_dir,
        log_path=log_path,
        seed=seed,
        documents=documents,
        missing=missing,
        stage_results=stage_results,
    )
    manifest["elapsed_seconds"] = round(time.time() - start, 3)
    write_json(output_dir / "enhanced_text_mining_summary.json", manifest)
    logger.event(
        "enhanced_text_mining",
        "completed",
        elapsed_seconds=manifest["elapsed_seconds"],
        summary=str(output_dir / "enhanced_text_mining_summary.json"),
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run enhanced open-source Part 2 text mining.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--enable-llm", action="store_true")
    parser.add_argument("--strict-models", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    manifest = run_enhanced_text_mining(
        dataset=args.dataset,
        output_dir=args.output_dir,
        log_path=args.log_path,
        seed=args.seed,
        enable_llm=args.enable_llm,
        continue_on_model_error=not args.strict_models,
    )
    print(
        json.dumps(
            {
                "collected_rows": manifest["collected_rows"],
                "missing_rows": manifest["missing_rows"],
                "output_dir": str(args.output_dir),
                "stage_statuses": {
                    key: value.get("status") for key, value in manifest["stage_results"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
