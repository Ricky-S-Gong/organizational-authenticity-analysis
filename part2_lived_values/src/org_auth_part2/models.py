"""Typed records shared across the Part 2 pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    ticker: str
    company_name: str
    sector: str
    primary_domain: str
    known_historical_domains: str = ""


@dataclass(frozen=True)
class CompanyYear:
    ticker: str
    company_name: str
    sector: str
    year: int


@dataclass(frozen=True)
class FilingMetadata:
    ticker: str
    cik: str
    company_name: str
    year: int
    form: str
    filing_date: str
    report_date: str
    accession_number: str
    primary_document: str
    source_url: str
    sec_archive_url: str


@dataclass(frozen=True)
class CollectionResult:
    ticker: str
    company_name: str
    sector: str
    year: int
    collection_status: str
    gap_reason: str
    cik: str = ""
    form: str = ""
    filing_date: str = ""
    report_date: str = ""
    accession_number: str = ""
    primary_document: str = ""
    source_url: str = ""
    sec_archive_url: str = ""
    raw_file_path: str = ""
    raw_file_bytes: int = 0
    raw_content_sha256: str = ""
    clean_text_sha256: str = ""
    text_path: str = ""
    page_text_clean: str = ""
    extraction_quality: str = ""
    word_count: int = 0
    sentence_count: int = 0
    theme_categories: str = ""
    theme_evidence: str = ""
    linguistic_metrics: str = ""
    analyst_notes: str = ""
