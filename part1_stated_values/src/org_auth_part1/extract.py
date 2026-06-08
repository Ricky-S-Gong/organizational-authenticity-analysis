"""Extract substantive visible text from archived corporate HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any

import trafilatura

_INVISIBLE_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}
_BOILERPLATE_TAGS = {"nav", "footer", "header", "aside"}
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "wbr",
}
_BLOCK_TAGS = {
    "article",
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "p",
    "section",
    "td",
    "th",
    "tr",
}
_BOILERPLATE_HINTS = re.compile(
    r"(?:^|[-_\s])(?:"
    r"breadcrumb|cookie|footer|header|menu|modal|nav|newsletter|"
    r"popup|privacy-banner|search|share|sidebar|social|subscribe"
    r")(?:$|[-_\s])",
    re.IGNORECASE,
)
_ERROR_PAGE_HINTS = re.compile(
    r"\b(?:404|page not found|page unavailable|access denied|temporarily unavailable)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"[ \t\f\v]+")
_HTML_TAGS = re.compile(r"<[^>]+>")
_SKIP_JSON_TEXT_KEYS = {
    "asset_id",
    "caption",
    "created_at",
    "height",
    "href",
    "id",
    "provider",
    "ratio",
    "slug",
    "src",
    "src_widths",
    "updated_at",
    "url",
    "video_id",
    "width",
}


@dataclass(frozen=True)
class ExtractionResult:
    """Auditable text extraction result and quality diagnostics."""

    visible_text_raw: str
    page_text_clean: str
    used_main_region: bool
    clean_word_count: int
    clean_char_count: int
    alpha_ratio: float
    link_text_ratio: float
    qa_flags: tuple[str, ...]
    extraction_backend: str


class _VisibleTextParser(HTMLParser):
    """HTMLParser-based extractor that separates visible, cleaned, and main text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, bool, bool, bool]] = []
        self.visible_parts: list[str] = []
        self.clean_parts: list[str] = []
        self.main_parts: list[str] = []
        self.visible_chars = 0
        self.link_chars = 0
        self.has_main_region = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "body":
            self._stack = []
            self.clean_parts = []
            self.main_parts = []
        attributes = {key.lower(): value or "" for key, value in attrs}
        attr_text = f"{attributes.get('id', '')} {attributes.get('class', '')}"
        hidden = (
            tag in _INVISIBLE_TAGS
            or "hidden" in attributes
            or attributes.get("aria-hidden", "").lower() == "true"
            or "display:none" in attributes.get("style", "").replace(" ", "").lower()
        )
        boilerplate = tag in _BOILERPLATE_TAGS or bool(_BOILERPLATE_HINTS.search(attr_text))
        in_main = tag in {"main", "article"} or attributes.get("role", "").lower() == "main"

        if self._stack:
            hidden = hidden or self._stack[-1][1]
            boilerplate = boilerplate or self._stack[-1][2]
            in_main = in_main or self._stack[-1][3]
        self.has_main_region = self.has_main_region or in_main
        if tag in _BLOCK_TAGS:
            self._add_separator()
        if tag not in _VOID_TAGS:
            self._stack.append((tag, hidden, boilerplate, in_main))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _BLOCK_TAGS:
            self._add_separator()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        text = _WHITESPACE.sub(" ", data).strip()
        if not text or not self._stack:
            return
        _, hidden, boilerplate, in_main = self._stack[-1]
        if hidden:
            return

        self.visible_parts.append(text)
        self.visible_chars += len(text)
        if any(item[0] == "a" for item in self._stack):
            self.link_chars += len(text)
        if not boilerplate:
            self.clean_parts.append(text)
            if in_main:
                self.main_parts.append(text)

    def _add_separator(self) -> None:
        for parts in (self.visible_parts, self.clean_parts, self.main_parts):
            if parts and parts[-1] != "\n":
                parts.append("\n")


def _normalize_parts(parts: list[str]) -> str:
    text = " ".join(parts)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _clean_json_string(value: str) -> str:
    text = _HTML_TAGS.sub(" ", unescape(value))
    text = re.sub(r"https?://\S+", " ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def extract_json_text(payload: Any, *, minimum_words: int = 3) -> str:
    """Extract readable narrative strings from archived JSON API payloads."""
    parts: list[str] = []
    seen: set[str] = set()

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key).lower())
            return
        if isinstance(value, list):
            for item in value:
                visit(item, key)
            return
        if not isinstance(value, str) or key in _SKIP_JSON_TEXT_KEYS:
            return
        text = _clean_json_string(value)
        if _word_count(text) < minimum_words:
            return
        normalized = text.casefold()
        if normalized in seen:
            return
        seen.add(normalized)
        parts.append(text)

    visit(payload)
    return "\n".join(parts)


def _trafilatura_fallback_text(html: str) -> str:
    """Use trafilatura only as an optional fallback when the local parser is too thin."""
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if extracted and _word_count(extracted) >= 25:
        return extracted.strip()
    recall_extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=False,
        favor_recall=True,
    )
    if recall_extracted and _word_count(recall_extracted) > _word_count(extracted or ""):
        return recall_extracted.strip()
    return extracted.strip() if extracted else ""


def extract_page_text(
    html: str,
    *,
    minimum_words: int = 75,
    enable_trafilatura_fallback: bool = False,
) -> ExtractionResult:
    """Extract substantive text and emit review-oriented QA flags.

    When a page contains a semantic ``main`` or ``article`` region, that region is
    preferred over the broader cleaned body. Flags identify suspicious outputs but
    do not silently discard them.
    """
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()

    visible_text = _normalize_parts(parser.visible_parts)
    main_text = _normalize_parts(parser.main_parts)
    broad_clean_text = _normalize_parts(parser.clean_parts)
    clean_text = main_text if main_text else broad_clean_text
    fallback_used = False
    if enable_trafilatura_fallback and _word_count(clean_text) < minimum_words:
        fallback_text = _trafilatura_fallback_text(html)
        if _word_count(fallback_text) > _word_count(clean_text):
            clean_text = fallback_text
            fallback_used = True

    words = re.findall(r"\b[\w'-]+\b", clean_text)
    alpha_chars = sum(character.isalpha() for character in clean_text)
    alpha_ratio = alpha_chars / len(clean_text) if clean_text else 0.0
    link_text_ratio = parser.link_chars / parser.visible_chars if parser.visible_chars else 0.0

    flags: list[str] = []
    if not clean_text:
        flags.append("empty_text")
    elif len(words) < minimum_words:
        flags.append("short_text")
    if clean_text and alpha_ratio < 0.5:
        flags.append("low_alpha_ratio")
    if link_text_ratio > 0.4:
        flags.append("high_link_text_ratio")
    if _ERROR_PAGE_HINTS.search(clean_text[:1000]):
        flags.append("likely_error_page")
    if not parser.has_main_region:
        flags.append("no_main_region")
    if fallback_used:
        flags.append("trafilatura_fallback")

    return ExtractionResult(
        visible_text_raw=visible_text,
        page_text_clean=clean_text,
        used_main_region=bool(main_text),
        clean_word_count=len(words),
        clean_char_count=len(clean_text),
        alpha_ratio=alpha_ratio,
        link_text_ratio=link_text_ratio,
        qa_flags=tuple(flags),
        extraction_backend="htmlparser+trafilatura" if fallback_used else "htmlparser",
    )
