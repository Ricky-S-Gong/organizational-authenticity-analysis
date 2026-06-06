"""Reproducible baseline utilities for Part 1 thematic and linguistic analysis.

The rules in this module are deliberately fixed and inspectable. They provide an
auditable baseline when no external LLM credentials are available; they are not
intended to replace human review of ambiguous language.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

TAXONOMY_VERSION = "1.0.0-keyword-baseline"


@dataclass(frozen=True)
class ThemeDefinition:
    """A stable multi-label theme definition with evidence-triggering phrases."""

    theme_id: str
    label: str
    description: str
    phrases: tuple[str, ...]


@dataclass(frozen=True)
class ThemeEvidence:
    """A theme assignment tied to a literal excerpt from the source text."""

    theme_id: str
    theme_label: str
    taxonomy_version: str
    matched_phrases: tuple[str, ...]
    evidence_excerpts: tuple[str, ...]
    match_count: int


THEME_TAXONOMY: tuple[ThemeDefinition, ...] = (
    ThemeDefinition(
        "customers_and_service",
        "Customers and service",
        "Serving customers, patients, clients, or consumers and improving their experience.",
        (
            "customer",
            "customers",
            "customer experience",
            "client",
            "clients",
            "consumer",
            "consumers",
            "patient",
            "patients",
            "service",
        ),
    ),
    ThemeDefinition(
        "employees_and_workplace",
        "Employees and workplace",
        "Supporting employees, talent, workplace culture, and professional growth.",
        (
            "employee",
            "employees",
            "our people",
            "workforce",
            "talent",
            "workplace",
            "professional development",
            "career development",
        ),
    ),
    ThemeDefinition(
        "innovation_and_excellence",
        "Innovation and excellence",
        "Pursuing innovation, quality, excellence, or continuous improvement.",
        (
            "innovation",
            "innovative",
            "invent",
            "excellence",
            "quality",
            "continuous improvement",
            "best in class",
        ),
    ),
    ThemeDefinition(
        "integrity_and_ethics",
        "Integrity and ethics",
        "Emphasizing integrity, ethics, honesty, trust, or transparent conduct.",
        (
            "integrity",
            "ethical",
            "ethics",
            "honesty",
            "honest",
            "trust",
            "transparent",
            "transparency",
        ),
    ),
    ThemeDefinition(
        "diversity_equity_and_inclusion",
        "Diversity, equity, and inclusion",
        "Advancing diversity, equity, inclusion, belonging, or equal opportunity.",
        (
            "diversity",
            "diverse",
            "equity",
            "inclusion",
            "inclusive",
            "belonging",
            "equal opportunity",
        ),
    ),
    ThemeDefinition(
        "social_impact_and_community",
        "Social impact and community",
        "Contributing to communities, society, philanthropy, or positive social impact.",
        (
            "community",
            "communities",
            "social impact",
            "society",
            "philanthropy",
            "volunteer",
            "giving back",
        ),
    ),
    ThemeDefinition(
        "environment_and_sustainability",
        "Environment and sustainability",
        "Addressing environmental sustainability, climate, emissions, or natural resources.",
        (
            "sustainability",
            "sustainable",
            "environment",
            "environmental",
            "climate",
            "emissions",
            "renewable",
            "natural resources",
        ),
    ),
    ThemeDefinition(
        "health_safety_and_wellbeing",
        "Health, safety, and wellbeing",
        "Protecting health, safety, security, or wellbeing.",
        (
            "health",
            "healthy",
            "safety",
            "safe",
            "wellbeing",
            "well-being",
            "security",
        ),
    ),
    ThemeDefinition(
        "shareholders_and_performance",
        "Shareholders and performance",
        "Creating shareholder value or emphasizing growth, performance, and returns.",
        (
            "shareholder",
            "shareholders",
            "shareholder value",
            "financial performance",
            "profitable growth",
            "long-term value",
            "returns",
        ),
    ),
    ThemeDefinition(
        "leadership_and_accountability",
        "Leadership and accountability",
        "Taking ownership, acting accountably, and demonstrating responsible leadership.",
        (
            "leadership",
            "leader",
            "leaders",
            "accountability",
            "accountable",
            "ownership",
            "responsibility",
            "responsible",
        ),
    ),
    ThemeDefinition(
        "collaboration_and_partnership",
        "Collaboration and partnership",
        "Working collaboratively through teamwork and partnerships.",
        (
            "collaboration",
            "collaborate",
            "teamwork",
            "partnership",
            "partnerships",
            "together",
        ),
    ),
    ThemeDefinition(
        "purpose_and_identity",
        "Purpose and identity",
        "Explicitly describing organizational purpose, mission, values, or identity.",
        (
            "our purpose",
            "our mission",
            "our values",
            "core values",
            "who we are",
            "we exist to",
            "our vision",
        ),
    ),
)

_WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_NUMBER_RE = re.compile(r"\b(?:\d+(?:[.,]\d+)*|percent|percentage)\b|%")

_LINGUISTIC_LEXICONS: dict[str, tuple[str, ...]] = {
    "first_person_plural": ("we", "our", "ours", "us"),
    "commitment": ("will", "must", "commit", "committed", "promise", "pledge"),
    "aspiration": ("aim", "aims", "aspire", "seek", "strive", "hope", "vision"),
    "action_or_evidence": (
        "achieved",
        "delivered",
        "launched",
        "reduced",
        "increased",
        "invest",
        "invested",
        "created",
        "implemented",
    ),
    "stakeholder": (
        "customer",
        "customers",
        "employee",
        "employees",
        "community",
        "communities",
        "supplier",
        "suppliers",
        "shareholder",
        "shareholders",
        "partner",
        "partners",
    ),
}


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text.strip()) if part.strip()]


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def _matching_excerpts(text: str, phrase: str) -> list[str]:
    pattern = _phrase_pattern(phrase)
    return [sentence for sentence in _sentences(text) if pattern.search(sentence)]


def classify_themes(text: str) -> list[ThemeEvidence]:
    """Assign all matching fixed themes and retain literal supporting excerpts."""

    results: list[ThemeEvidence] = []
    for theme in THEME_TAXONOMY:
        matched_phrases: list[str] = []
        excerpts: list[str] = []
        match_count = 0
        for phrase in theme.phrases:
            pattern = _phrase_pattern(phrase)
            matches = pattern.findall(text)
            if not matches:
                continue
            matched_phrases.append(phrase)
            match_count += len(matches)
            excerpts.extend(_matching_excerpts(text, phrase))
        if matched_phrases:
            results.append(
                ThemeEvidence(
                    theme_id=theme.theme_id,
                    theme_label=theme.label,
                    taxonomy_version=TAXONOMY_VERSION,
                    matched_phrases=tuple(matched_phrases),
                    evidence_excerpts=tuple(dict.fromkeys(excerpts)),
                    match_count=match_count,
                )
            )
    return results


def linguistic_metrics(text: str) -> dict[str, float | int]:
    """Compute deterministic, dependency-free linguistic indicators."""

    words = [word.casefold() for word in _WORD_RE.findall(text)]
    sentences = _sentences(text)
    word_count = len(words)

    metrics: dict[str, float | int] = {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "average_sentence_length": round(word_count / len(sentences), 4) if sentences else 0.0,
        "quantified_claim_count": len(_NUMBER_RE.findall(text.casefold())),
    }
    for name, lexicon in _LINGUISTIC_LEXICONS.items():
        count = sum(words.count(term) for term in lexicon)
        metrics[f"{name}_count"] = count
        metrics[f"{name}_rate_per_100_words"] = (
            round(100 * count / word_count, 4) if word_count else 0.0
        )
    return metrics


def analyze_text(text: str) -> dict[str, Any]:
    """Return a JSON-serializable thematic and linguistic baseline analysis."""

    theme_evidence = classify_themes(text)
    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "theme_categories": [evidence.theme_id for evidence in theme_evidence],
        "theme_evidence": [asdict(evidence) for evidence in theme_evidence],
        "linguistic_metrics": linguistic_metrics(text),
    }


def analyze_records(
    records: Sequence[Mapping[str, Any]], text_field: str = "page_text_clean"
) -> list[dict[str, Any]]:
    """Enrich usable records without classifying missing or unusable observations."""

    enriched: list[dict[str, Any]] = []
    for record in records:
        result = dict(record)
        text = record.get(text_field)
        if record.get("collection_status") == "usable" and isinstance(text, str) and text.strip():
            result.update(analyze_text(text))
        else:
            result.update(
                {
                    "taxonomy_version": TAXONOMY_VERSION,
                    "theme_categories": None,
                    "theme_evidence": None,
                    "linguistic_metrics": None,
                }
            )
        enriched.append(result)
    return enriched
