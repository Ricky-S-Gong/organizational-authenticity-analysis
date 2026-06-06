"""Typed data contracts shared across the Part 1 pipeline."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Sector(StrEnum):
    TECHNOLOGY = "Technology"
    FINANCIALS = "Financials"
    HEALTHCARE = "Healthcare"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    ENERGY = "Energy"


class ObservationStatus(StrEnum):
    PENDING = "pending"
    USABLE = "usable"
    NO_CDX_CAPTURE = "no_cdx_capture"
    NO_ELIGIBLE_PAGE = "no_eligible_page"
    RETRIEVAL_FAILED = "retrieval_failed"
    REDIRECT_UNRESOLVED = "redirect_unresolved"
    NON_HTML_CAPTURE = "non_html_capture"
    SOFT_404_OR_ERROR_PAGE = "soft_404_or_error_page"
    INSUFFICIENT_SUBSTANTIVE_TEXT = "insufficient_substantive_text"
    EXTRACTION_FAILED = "extraction_failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class Company(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    company_name: str
    sector: Sector
    primary_domain: str
    known_historical_domains: list[str] = Field(default_factory=list)

    @field_validator("ticker", "primary_domain")
    @classmethod
    def require_value(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value


class CompanyYearTarget(BaseModel):
    ticker: str
    company_name: str
    sector: Sector
    year: int = Field(ge=2016, le=2024)
    target_timestamp: datetime
    observation_status: ObservationStatus = ObservationStatus.PENDING


class CdxCapture(BaseModel):
    timestamp: datetime
    original_url: str
    status_code: int | None = None
    mime_type: str | None = None
    digest: str | None = None
    length: int | None = None

    @property
    def year(self) -> int:
        return self.timestamp.year

    def is_html_success(self) -> bool:
        return self.status_code == 200 and self.mime_type in {"text/html", "application/xhtml+xml"}


class PageCandidate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ticker: str
    candidate_url: str
    page_type: str
    valid_from_year: int = Field(default=2016, ge=2016, le=2024)
    valid_to_year: int = Field(default=2024, ge=2016, le=2024)
    discovery_method: str
    eligibility_status: str
    eligibility_reason: str
    reviewer: str

    @field_validator("candidate_url")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("candidate URL must use http or https")
        return value
