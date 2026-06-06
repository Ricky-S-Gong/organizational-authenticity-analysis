"""Deterministically rank eligible CDX captures for an annual target."""

from datetime import datetime

from org_auth_part1.models import CdxCapture


def rank_annual_captures(
    captures: list[CdxCapture], target_timestamp: datetime
) -> list[CdxCapture]:
    """Return eligible same-year captures ranked nearest to the target timestamp."""
    eligible = [
        capture
        for capture in captures
        if capture.year == target_timestamp.year and capture.is_html_success()
    ]
    return sorted(
        eligible,
        key=lambda capture: (
            abs(capture.timestamp - target_timestamp),
            capture.timestamp,
            capture.original_url,
        ),
    )


def select_annual_capture(
    captures: list[CdxCapture], target_timestamp: datetime
) -> CdxCapture | None:
    ranked = rank_annual_captures(captures, target_timestamp)
    return ranked[0] if ranked else None
