"""Create tables and figures for enhanced Part 2 model checks."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from org_auth_part2.presentation import fmt, write_table_set
from org_auth_part2.targets import PART2_ROOT

DEFAULT_ENHANCED_DIR = PART2_ROOT / "outputs/text_mining/enhanced"
DEFAULT_TABLE_DIR = DEFAULT_ENHANCED_DIR / "tables"
DEFAULT_FIGURE_DIR = DEFAULT_ENHANCED_DIR / "figures"
DEFAULT_ANALYSIS_DOC = PART2_ROOT / "docs/text_mining_analysis.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def short_terms(value: str, limit: int = 7) -> str:
    terms = [term.strip() for term in value.split(";") if term.strip()]
    return "; ".join(terms[:limit])


def build_enhanced_tables(enhanced_dir: Path, table_dir: Path) -> dict[str, Any]:
    topics = read_csv(enhanced_dir / "nmf_topics.csv")
    shifts = read_csv(enhanced_dir / "embedding_adjacent_year_shifts.csv")
    llm_rows = read_csv(enhanced_dir / "llm_annotations.csv")
    summary = json.loads((enhanced_dir / "enhanced_text_mining_summary.json").read_text())

    topic_totals = {
        row["topic_id"]: float(row["total_score"])
        for row in summary["stage_results"]["tfidf_nmf"]["dominant_corpus_topics"]
    }
    topic_rows = [
        [
            row["topic_id"].replace("nmf_topic_", "T"),
            fmt(topic_totals[row["topic_id"]]),
            short_terms(row["top_terms"]),
        ]
        for row in sorted(topics, key=lambda item: topic_totals[item["topic_id"]], reverse=True)
    ]
    write_table_set(
        table_dir,
        "enhanced_nmf_topics",
        ["Topic", "Corpus score", "Top terms"],
        topic_rows,
        "NMF topics estimated from representative proxy-statement text windows.",
    )

    shift_rows = [
        [
            row["ticker"],
            f"{row['prior_year']}-{row['year']}",
            row["sector"],
            fmt(row["semantic_distance"], 3),
            fmt(row["cosine_similarity"], 3),
        ]
        for row in shifts[:10]
    ]
    write_table_set(
        table_dir,
        "enhanced_embedding_shifts",
        ["Ticker", "Years", "Sector", "Semantic distance", "Cosine similarity"],
        shift_rows,
        "Largest adjacent-year semantic shifts from MiniLM document embeddings.",
    )

    quality_counts = Counter(row["annotation_quality_flag"] for row in llm_rows)
    quality_rows = [
        [quality, str(count), f"{count / len(llm_rows):.1%}"]
        for quality, count in sorted(quality_counts.items())
    ]
    write_table_set(
        table_dir,
        "enhanced_llm_quality",
        ["Quality flag", "Count", "Share"],
        quality_rows,
        "Quality flags for sampled local FLAN-T5 annotations.",
    )
    return {
        "topics": topics,
        "topic_totals": topic_totals,
        "shifts": shifts,
        "llm_quality_counts": quality_counts,
        "topic_rows": topic_rows,
        "shift_rows": shift_rows,
        "quality_rows": quality_rows,
        "summary": summary,
    }


def _set_plot_style() -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )


def write_enhanced_figures(payload: dict[str, Any], figure_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt
    import seaborn as sns

    _set_plot_style()
    figure_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    ordered_topics = sorted(
        payload["topics"],
        key=lambda row: payload["topic_totals"][row["topic_id"]],
        reverse=True,
    )
    topic_labels = [
        row["topic_id"].replace("nmf_topic_", "T") + ": " + row["topic_label"].split(" / ")[0]
        for row in ordered_topics
    ]
    topic_scores = [payload["topic_totals"][row["topic_id"]] for row in ordered_topics]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    sns.barplot(x=topic_scores, y=topic_labels, ax=ax, color="#2563eb")
    ax.set_title("NMF Topic Prevalence in Proxy Statements")
    ax.set_xlabel("Total NMF topic score across collected company-years")
    ax.set_ylabel("")
    ax.bar_label(ax.containers[0], fmt="%.1f", padding=3, fontsize=8)
    fig.tight_layout()
    path = figure_dir / "enhanced_nmf_topic_scores.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    written.append(path)

    shifts = payload["shifts"][:10]
    labels = [f"{row['ticker']} {row['prior_year']}-{row['year']}" for row in shifts]
    distances = [float(row["semantic_distance"]) for row in shifts]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    sns.barplot(x=distances, y=labels, ax=ax, color="#dc2626")
    ax.set_title("Largest Adjacent-Year Semantic Shifts")
    ax.set_xlabel("1 - cosine similarity from MiniLM embeddings")
    ax.set_ylabel("")
    ax.bar_label(ax.containers[0], fmt="%.3f", padding=3, fontsize=8)
    fig.tight_layout()
    path = figure_dir / "enhanced_embedding_shifts.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    written.append(path)

    quality_counts = payload["llm_quality_counts"]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    labels = list(quality_counts)
    counts = [quality_counts[label] for label in labels]
    sns.barplot(x=counts, y=labels, ax=ax, color="#16a34a")
    ax.set_title("Local FLAN-T5 Annotation Quality Flags")
    ax.set_xlabel("Sampled annotations")
    ax.set_ylabel("")
    ax.bar_label(ax.containers[0], fmt="%.0f", padding=3, fontsize=8)
    fig.tight_layout()
    path = figure_dir / "enhanced_llm_quality.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    written.append(path)

    return written


def enhanced_section_markdown(payload: dict[str, Any], table_dir: Path, figure_dir: Path) -> str:
    figures_rel = "../outputs/text_mining/enhanced/figures"
    summary = payload["summary"]
    stage_results = summary["stage_results"]
    tfidf = stage_results.get("tfidf_nmf", {})
    embedding = stage_results.get("sentence_embeddings", {})
    spacy = stage_results.get("spacy_pipeline", {})
    llm = stage_results.get("local_llm_annotations", {})
    embedding_model = embedding.get("parameters", {}).get("model_name", "not_run")
    spacy_model = spacy.get("parameters", {}).get("model_name", "not_run")
    return f"""## 7. Enhanced Model-Based Checks

This section merges the exploratory open-source NLP/modeling layer into the main Part 2 analysis.
It adds TF-IDF/NMF topic modeling, sentence-transformer embeddings, spaCy statistical features, and
a sampled local FLAN-T5 annotation pass on top of the deterministic phrase-evidence baseline.
These outputs are interpretive aids, not replacements for the baseline theme evidence.

The enhanced run covers {summary["collected_rows"]} collected company-years. All parameters,
package versions, model names, seed values, input hashes, and output paths are recorded in
`outputs/text_mining/enhanced/enhanced_text_mining_summary.json`; the JSONL progress log is
`data/interim/enhanced_text_mining_run_log.jsonl`. All stochastic stages use seed
`{summary["seed"]}` and the input dataset hash is `{summary["dataset_sha256"]}`.

Stage status summary:

- TF-IDF/NMF: `{tfidf.get("status", "not_run")}` with seed `{summary["seed"]}`.
- Sentence embeddings: `{embedding.get("status", "not_run")}` using `{embedding_model}`.
- spaCy features: `{spacy.get("status", "not_run")}` using `{spacy_model}`.
- Local LLM annotations: `{llm.get("status", "not_run")}`; sampled outputs are marked with quality
  flags and `needs_human_review`.

![NMF topic prevalence]({figures_rel}/enhanced_nmf_topic_scores.png)

{(table_dir / "enhanced_nmf_topics.md").read_text(encoding="utf-8")}

The NMF results deepen the construct-validity reading rather than replacing the baseline. The
highest-scoring topic is not a pure value construct; it mixes strategy, shareholders, company, and
financial scale language. Other topics recover stockholder meeting mechanics, forward-looking
statement boilerplate, annual general meeting language, and company-specific templates. In other
words, in `DEF 14A`, lived-values language is embedded inside governance machinery rather than
presented as a clean cultural manifesto.

![Embedding semantic shifts]({figures_rel}/enhanced_embedding_shifts.png)

{(table_dir / "enhanced_embedding_shifts.md").read_text(encoding="utf-8")}

The embedding layer is useful as a triage device. Large semantic distances point to filings whose
overall disclosure profile changed enough to justify qualitative review. Target 2021-2022, Valero
2021-2022, and JPMorgan 2022-2023 are the strongest model-identified candidates. These shifts are
not theme labels by themselves; they are pointers to company-year pairs where the surrounding
sections should be read manually.

![LLM annotation quality]({figures_rel}/enhanced_llm_quality.png)

{(table_dir / "enhanced_llm_quality.md").read_text(encoding="utf-8")}

The local LLM check is most useful as a negative audit result. Although the run is fully logged
with model name, seed, temperature, prompt hash, excerpt hash, and response hash, most sampled
annotations were empty, fragmentary, or boilerplate-like. Only one sampled output was flagged as a
candidate interpretive signal. This means the small local model should not carry any Part 2 claim;
it is retained as a transparent exploratory layer and a warning against over-reading cheap LLM
annotations in legal disclosure text.

For reproducibility, rerun the enhanced stage from the same `uv.lock`, the same input dataset hash,
and the parameters in `enhanced_text_mining_summary.json`. Model downloads are free/open-source but
still depend on package and model availability at rerun time.
"""


def update_analysis_doc(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    marker_options = ("## 7. Enhanced Model-Based Checks", "## 6. Enhanced Model-Based Checks")
    end = text.index("## Interpretation")
    start = next(
        (text.index(marker) for marker in marker_options if marker in text),
        end,
    )
    path.write_text(text[:start] + section + "\n" + text[end:], encoding="utf-8")


def run_enhanced_presentation(
    enhanced_dir: Path = DEFAULT_ENHANCED_DIR,
    table_dir: Path = DEFAULT_TABLE_DIR,
    figure_dir: Path = DEFAULT_FIGURE_DIR,
    analysis_doc: Path = DEFAULT_ANALYSIS_DOC,
) -> dict[str, Any]:
    payload = build_enhanced_tables(enhanced_dir, table_dir)
    figures = write_enhanced_figures(payload, figure_dir)
    section = enhanced_section_markdown(payload, table_dir, figure_dir)
    update_analysis_doc(analysis_doc, section)
    return {
        "table_dir": str(table_dir),
        "figure_dir": str(figure_dir),
        "analysis_doc": str(analysis_doc),
        "figures": [str(path) for path in figures],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build enhanced Part 2 tables and figures.")
    parser.add_argument("--enhanced-dir", type=Path, default=DEFAULT_ENHANCED_DIR)
    parser.add_argument("--table-dir", type=Path, default=DEFAULT_TABLE_DIR)
    parser.add_argument("--figure-dir", type=Path, default=DEFAULT_FIGURE_DIR)
    parser.add_argument("--analysis-doc", type=Path, default=DEFAULT_ANALYSIS_DOC)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = run_enhanced_presentation(
        enhanced_dir=args.enhanced_dir,
        table_dir=args.table_dir,
        figure_dir=args.figure_dir,
        analysis_doc=args.analysis_doc,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
