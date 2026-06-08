"""Section-level proxy parsing for Part 4.

The parser is heuristic rather than filing-template specific. It identifies likely section
headings from extracted proxy text, assigns each section to a research-oriented family, and
computes genre/theme diagnostics inside each section. The goal is to determine which parts of the
proxy statement contribute most to the values-theme evidence used downstream.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from org_auth_part4.analysis import count_phrase_matches, load_part2_with_text, normalize_text
from org_auth_part4.constants import (
    GENRE_DICTIONARIES,
    SECTION_OUTPUT,
    SECTION_PATTERNS,
    SECTION_SUMMARY_OUTPUT,
    THEME_DICTIONARIES,
)

WORD_RE = re.compile(r"\b[\w'-]+\b")


@dataclass(frozen=True)
class ParsedSection:
    """A section-like text span extracted from a proxy statement."""

    title: str
    family: str
    text: str
    order: int


def word_count(text: str) -> int:
    """Count words in a text span."""

    return len(WORD_RE.findall(str(text)))


def classify_section(title: str, text: str = "") -> str:
    """Classify a heading/text span into a proxy section family."""

    title_text = normalize_text(title)
    # Prefer headings over body text because headings are the strongest cue about a section's
    # disclosure function; body text is only a backup for noisy or generic headings.
    for family, phrases in SECTION_PATTERNS.items():
        if any(phrase in title_text for phrase in phrases):
            return family
    haystack = normalize_text(f"{title} {text[:1500]}")
    for family, phrases in SECTION_PATTERNS.items():
        if any(phrase in haystack for phrase in phrases):
            return family
    return "other"


def is_heading(line: str) -> bool:
    """Return whether a line looks like a proxy section heading."""

    stripped = " ".join(str(line).split())
    # Proxy extraction often produces short table cells and long wrapped sentences. The length and
    # word-count filters remove most of those before applying capitalization/keyword cues.
    if not stripped or len(stripped) > 140:
        return False
    words = WORD_RE.findall(stripped)
    if len(words) < 2 or len(words) > 18:
        return False
    lowered = stripped.lower()
    letters = [char for char in stripped if char.isalpha()]
    if not letters:
        return False
    upper_share = sum(char.isupper() for char in letters) / len(letters)
    title_cap_share = sum(word[:1].isupper() for word in words) / len(words)
    if stripped.endswith((".", ",")) and upper_share < 0.65:
        return False
    if any(phrase in lowered for phrases in SECTION_PATTERNS.values() for phrase in phrases):
        # Known section terms are allowed with either uppercase layout or title-case layout because
        # companies vary widely in how SEC HTML tables preserve headings.
        return upper_share >= 0.65 or title_cap_share >= 0.45 or len(words) <= 7
    title_like = stripped[:1].isupper() and title_cap_share >= 0.45
    return upper_share >= 0.65 or title_like


def fallback_chunks(text: str, *, chunk_words: int = 1800) -> list[ParsedSection]:
    """Split text into classified chunks when heading detection is too sparse."""

    words = WORD_RE.findall(str(text))
    sections: list[ParsedSection] = []
    for order, start in enumerate(range(0, len(words), chunk_words)):
        chunk = " ".join(words[start : start + chunk_words])
        # Fallback chunks preserve document coverage when heading detection fails; they are marked
        # with synthetic titles so downstream users can distinguish them from detected headings.
        family = classify_section(f"chunk {order + 1}", chunk)
        sections.append(
            ParsedSection(
                title=f"Fallback chunk {order + 1}",
                family=family,
                text=chunk,
                order=order,
            )
        )
    return sections


def parse_proxy_sections(text: str) -> list[ParsedSection]:
    """Parse a proxy statement into section-like spans."""

    if not normalize_text(text):
        return []
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    heading_positions = [idx for idx, line in enumerate(lines) if is_heading(line)]
    sections: list[ParsedSection] = []
    for order, start in enumerate(heading_positions):
        end = heading_positions[order + 1] if order + 1 < len(heading_positions) else len(lines)
        title = lines[start]
        body = "\n".join(lines[start + 1 : end])
        # Very short spans are usually table-of-contents fragments or extracted table labels rather
        # than substantive section bodies, so they are excluded from section diagnostics.
        if word_count(body) < 20:
            continue
        sections.append(
            ParsedSection(
                title=title[:140],
                family=classify_section(title, body),
                text=body,
                order=order,
            )
        )
    if len(sections) < 3:
        return fallback_chunks(text)
    return sections


def _dominant_theme(theme_counts: dict[str, int]) -> tuple[str, int]:
    """Return the leading theme ID and count for one section."""

    positive = [(theme_id, count) for theme_id, count in theme_counts.items() if count > 0]
    if not positive:
        return "", 0
    positive.sort(key=lambda item: (-item[1], item[0]))
    return positive[0]


def section_records_for_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Build section-level records for one proxy row."""

    text = row.get("page_text_clean") or ""
    sections = parse_proxy_sections(text)
    total_words = max(int(row.get("word_count") or word_count(text)), 0)
    if not sections:
        # Keep one explicit missing row for collected proxies whose text cannot be parsed. This
        # mirrors the project-wide rule of retaining failed company-years with auditable statuses.
        return [
            {
                "ticker": row["ticker"],
                "company_name": row["company_name"],
                "sector": row["sector"],
                "year": int(row["year"]),
                "section_status": "missing_proxy_text",
                "section_order": None,
                "section_family": "",
                "section_title": "",
                "section_word_count": 0,
                "section_share_of_proxy": 0.0,
                "section_genre_count": 0,
                "section_genre_rate": 0.0,
                "dominant_theme_id": "",
                "dominant_theme_count": 0,
                "total_theme_matches": 0,
            }
        ]

    records = []
    for section in sections:
        section_words = word_count(section.text)
        # Section rows carry both genre and values-theme counts so the diagnostics can separate
        # procedural proxy machinery from the locations where values evidence is most concentrated.
        genre_count = sum(
            count_phrase_matches(section.text, phrases) for phrases in GENRE_DICTIONARIES.values()
        )
        theme_counts = {
            theme_id: count_phrase_matches(section.text, phrases)
            for theme_id, phrases in THEME_DICTIONARIES.items()
        }
        dominant_theme, dominant_count = _dominant_theme(theme_counts)
        record = {
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "sector": row["sector"],
            "year": int(row["year"]),
            "section_status": "parsed",
            "section_order": section.order,
            "section_family": section.family,
            "section_title": section.title,
            "section_word_count": section_words,
            "section_share_of_proxy": round(section_words / total_words, 6)
            if total_words
            else 0.0,
            "section_genre_count": genre_count,
            "section_genre_rate": round(1000 * genre_count / section_words, 6)
            if section_words
            else 0.0,
            "dominant_theme_id": dominant_theme,
            "dominant_theme_count": dominant_count,
            "total_theme_matches": sum(theme_counts.values()),
        }
        for theme_id, count in theme_counts.items():
            record[f"theme_{theme_id}_count"] = count
        records.append(record)
    return records


def build_section_diagnostics() -> pd.DataFrame:
    """Build long-format section diagnostics for all collected proxy statements."""

    part2 = load_part2_with_text()
    rows: list[dict[str, Any]] = []
    for row in part2.to_dict("records"):
        if row.get("collection_status") != "collected":
            continue
        rows.extend(section_records_for_row(row))
    return pd.DataFrame(rows)


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Return weighted mean with a zero-safe denominator."""

    denominator = weights.sum()
    if denominator <= 0:
        return 0.0
    return round(float((values * weights).sum() / denominator), 6)


def build_section_summary(section_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize section families across parsed proxy statements."""

    parsed = section_frame[section_frame["section_status"] == "parsed"].copy()
    rows = []
    for family, group in parsed.groupby("section_family", sort=True):
        rows.append(
            {
                "section_family": family,
                "section_rows": len(group),
                "company_years": group[["ticker", "year"]].drop_duplicates().shape[0],
                "total_words": int(group["section_word_count"].sum()),
                "mean_section_share_of_proxy": round(group["section_share_of_proxy"].mean(), 6),
                "weighted_genre_rate": _weighted_mean(
                    group["section_genre_rate"], group["section_word_count"]
                ),
                "total_theme_matches": int(group["total_theme_matches"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("total_words", ascending=False)


def write_section_outputs() -> dict[str, str]:
    """Write section-level Part 4 outputs."""

    sections = build_section_diagnostics()
    summary = build_section_summary(sections)
    SECTION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sections.to_csv(SECTION_OUTPUT, index=False)
    summary.to_csv(SECTION_SUMMARY_OUTPUT, index=False)
    return {
        str(SECTION_OUTPUT): str(len(sections)),
        str(SECTION_SUMMARY_OUTPUT): str(len(summary)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(write_section_outputs(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
