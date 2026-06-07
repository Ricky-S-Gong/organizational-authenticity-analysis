"""HTML text extraction for SEC filing documents."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_SPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINE_RE = re.compile(r"\n{3,}")


class VisibleTextParser(HTMLParser):
    """Extract visible filing text without requiring a browser renderer."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style", "noscript", "ix:header", "head"}:
            self._hidden_depth += 1
        if tag_name in {
            "p",
            "div",
            "br",
            "tr",
            "table",
            "section",
            "article",
            "h1",
            "h2",
            "h3",
        }:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style", "noscript", "ix:header", "head"} and self._hidden_depth:
            self._hidden_depth -= 1
        if tag_name in {"p", "div", "tr", "table", "section", "article", "h1", "h2", "h3"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth and data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        return clean_text(" ".join(self._chunks))


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph-like line breaks."""

    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = _SPACE_RE.sub(" ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = _BLANK_LINE_RE.sub("\n\n", text)
    return text.strip()


def extract_visible_text(content: bytes, content_type: str = "") -> str:
    """Extract clean text from either HTML filings or plain-text artifacts."""

    decoded = content.decode("utf-8", errors="replace")
    if "html" not in content_type.lower() and not re.search(
        r"<html|<body|<document",
        decoded,
        re.I,
    ):
        return clean_text(decoded)
    parser = VisibleTextParser()
    parser.feed(decoded)
    return parser.text()


def extraction_quality(text: str, minimum_words: int = 1000) -> str:
    """Classify extraction quality using conservative, auditable thresholds."""

    words = len(re.findall(r"\b[\w'-]+\b", text))
    if words == 0:
        return "empty"
    if words < minimum_words:
        return "insufficient_text"
    if "TABLE OF CONTENTS" in text[:5000].upper() and words < 2500:
        return "possibly_index_only"
    return "usable"
