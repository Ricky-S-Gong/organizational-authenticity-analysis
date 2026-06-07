"""Auditable Part 2 theme and linguistic analysis.

The theme taxonomy intentionally mirrors Part 1 version 1.0.0 so Part 3 can compare
stated-values pages and proxy disclosures with a shared representation.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

TAXONOMY_VERSION = "1.0.0-keyword-baseline"


@dataclass(frozen=True)
class ThemeDefinition:
    theme_id: str
    label: str
    phrases: tuple[str, ...]


@dataclass(frozen=True)
class ThemeEvidence:
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
        ("health", "healthy", "safety", "safe", "wellbeing", "well-being", "security"),
    ),
    ThemeDefinition(
        "shareholders_and_performance",
        "Shareholders and performance",
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
        ("collaboration", "collaborate", "teamwork", "partnership", "partnerships", "together"),
    ),
    ThemeDefinition(
        "purpose_and_identity",
        "Purpose and identity",
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
    ),
}


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_RE.split(text) if sentence.strip()]


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def assign_themes(text: str) -> list[ThemeEvidence]:
    sentences = split_sentences(text)
    assigned: list[ThemeEvidence] = []
    for theme in THEME_TAXONOMY:
        matched_phrases: list[str] = []
        excerpts: list[str] = []
        match_count = 0
        for phrase in theme.phrases:
            pattern = _phrase_pattern(phrase)
            phrase_matches = pattern.findall(text)
            if not phrase_matches:
                continue
            matched_phrases.append(phrase)
            match_count += len(phrase_matches)
            for sentence in sentences:
                if pattern.search(sentence) and sentence not in excerpts:
                    excerpts.append(sentence[:500])
                if len(excerpts) >= 8:
                    break
        if match_count:
            assigned.append(
                ThemeEvidence(
                    theme_id=theme.theme_id,
                    theme_label=theme.label,
                    taxonomy_version=TAXONOMY_VERSION,
                    matched_phrases=tuple(matched_phrases),
                    evidence_excerpts=tuple(excerpts),
                    match_count=match_count,
                )
            )
    return assigned


def linguistic_metrics(text: str) -> dict[str, Any]:
    words = [word.lower() for word in _WORD_RE.findall(text)]
    sentences = split_sentences(text)
    metrics: dict[str, Any] = {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "average_sentence_length": round(len(words) / len(sentences), 3) if sentences else 0,
        "quantified_claim_count": len(_NUMBER_RE.findall(text)),
    }
    for name, lexicon in _LINGUISTIC_LEXICONS.items():
        count = sum(1 for word in words if word in lexicon)
        metrics[f"{name}_count"] = count
        metrics[f"{name}_rate_per_100_words"] = round((count / len(words)) * 100, 4) if words else 0
    return metrics


def analysis_json(text: str) -> tuple[str, str, str]:
    themes = assign_themes(text)
    categories = json.dumps([theme.theme_id for theme in themes], ensure_ascii=True)
    evidence = json.dumps([asdict(theme) for theme in themes], ensure_ascii=True)
    metrics = json.dumps(linguistic_metrics(text), ensure_ascii=True, sort_keys=True)
    return categories, evidence, metrics
