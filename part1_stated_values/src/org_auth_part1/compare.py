"""Deterministic adjacent-year change metrics for cleaned page text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum

_TOKEN_PATTERN = re.compile(r"\b[\w'-]+\b")
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")


class ChangeClass(StrEnum):
    NO_PRIOR = "no_prior"
    INDETERMINATE = "indeterminate"
    UNCHANGED_EXACT = "unchanged_exact"
    MINOR_EDIT = "minor_edit"
    SUBSTANTIVE_CHANGE = "substantive_change"


@dataclass(frozen=True)
class ChangeComparison:
    year: int
    prior_year: int | None
    change_class: ChangeClass
    changed_from_prior: bool | None
    exact_match: bool | None
    token_jaccard_similarity: float | None
    edit_similarity: float | None
    word_count_delta_ratio: float | None
    added_snippets: tuple[str, ...] = ()
    removed_snippets: tuple[str, ...] = ()


def normalize_for_comparison(text: str) -> str:
    """Normalize formatting noise without altering substantive wording."""
    return " ".join(text.casefold().split())


def _tokens(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(normalize_for_comparison(text))


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_PATTERN.split(text) if sentence.strip()]


def _jaccard(left: list[str], right: list[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 1.0


def _evidence_snippets(
    prior_text: str, current_text: str, *, maximum_snippets: int = 3
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    prior_sentences = _sentences(prior_text)
    current_sentences = _sentences(current_text)
    matcher = SequenceMatcher(
        None,
        [normalize_for_comparison(sentence) for sentence in prior_sentences],
        [normalize_for_comparison(sentence) for sentence in current_sentences],
        autojunk=False,
    )
    added: list[str] = []
    removed: list[str] = []
    for tag, prior_start, prior_end, current_start, current_end in matcher.get_opcodes():
        if tag in {"insert", "replace"}:
            added.extend(current_sentences[current_start:current_end])
        if tag in {"delete", "replace"}:
            removed.extend(prior_sentences[prior_start:prior_end])
    return tuple(added[:maximum_snippets]), tuple(removed[:maximum_snippets])


def compare_texts(
    prior_text: str,
    current_text: str,
    *,
    year: int,
    prior_year: int,
    minor_edit_threshold: float = 0.9,
) -> ChangeComparison:
    """Compare usable cleaned texts and classify their substantive change."""
    prior_normalized = normalize_for_comparison(prior_text)
    current_normalized = normalize_for_comparison(current_text)
    prior_tokens = _tokens(prior_text)
    current_tokens = _tokens(current_text)

    exact_match = prior_normalized == current_normalized
    jaccard = _jaccard(prior_tokens, current_tokens)
    edit_similarity = SequenceMatcher(
        None, prior_normalized, current_normalized, autojunk=False
    ).ratio()
    word_delta_ratio = (
        (len(current_tokens) - len(prior_tokens)) / len(prior_tokens) if prior_tokens else 0.0
    )
    combined_similarity = min(jaccard, edit_similarity)

    if exact_match:
        change_class = ChangeClass.UNCHANGED_EXACT
    elif combined_similarity >= minor_edit_threshold:
        change_class = ChangeClass.MINOR_EDIT
    else:
        change_class = ChangeClass.SUBSTANTIVE_CHANGE

    added, removed = _evidence_snippets(prior_text, current_text)
    return ChangeComparison(
        year=year,
        prior_year=prior_year,
        change_class=change_class,
        changed_from_prior=change_class is not ChangeClass.UNCHANGED_EXACT,
        exact_match=exact_match,
        token_jaccard_similarity=jaccard,
        edit_similarity=edit_similarity,
        word_count_delta_ratio=word_delta_ratio,
        added_snippets=added,
        removed_snippets=removed,
    )


def compare_adjacent_years(year_texts: dict[int, str | None]) -> list[ChangeComparison]:
    """Compare each year only with the immediately preceding calendar year."""
    comparisons: list[ChangeComparison] = []
    for year in sorted(year_texts):
        prior_year = year - 1
        current_text = year_texts[year]
        if prior_year not in year_texts:
            comparisons.append(
                ChangeComparison(
                    year=year,
                    prior_year=None,
                    change_class=ChangeClass.NO_PRIOR,
                    changed_from_prior=None,
                    exact_match=None,
                    token_jaccard_similarity=None,
                    edit_similarity=None,
                    word_count_delta_ratio=None,
                )
            )
        elif not current_text or not year_texts[prior_year]:
            comparisons.append(
                ChangeComparison(
                    year=year,
                    prior_year=prior_year,
                    change_class=ChangeClass.INDETERMINATE,
                    changed_from_prior=None,
                    exact_match=None,
                    token_jaccard_similarity=None,
                    edit_similarity=None,
                    word_count_delta_ratio=None,
                )
            )
        else:
            comparisons.append(
                compare_texts(
                    year_texts[prior_year] or "",
                    current_text,
                    year=year,
                    prior_year=prior_year,
                )
            )
    return comparisons
