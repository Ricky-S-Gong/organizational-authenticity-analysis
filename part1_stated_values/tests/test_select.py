from datetime import UTC, datetime

from org_auth_part1.models import CdxCapture
from org_auth_part1.select import rank_annual_captures, select_annual_capture


def capture(timestamp: str, status_code: int = 200, mime_type: str = "text/html") -> CdxCapture:
    return CdxCapture(
        timestamp=datetime.fromisoformat(timestamp),
        original_url=f"https://example.com/about?capture={timestamp}",
        status_code=status_code,
        mime_type=mime_type,
    )


def test_selects_nearest_valid_same_year_capture() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)
    captures = [
        capture("2020-01-01T00:00:00+00:00"),
        capture("2020-07-01T00:00:00+00:00"),
        capture("2020-06-29T00:00:00+00:00"),
        capture("2021-06-30T12:00:00+00:00"),
        capture("2020-06-30T12:00:00+00:00", status_code=302),
    ]

    selected = select_annual_capture(captures, target)

    assert selected is not None
    assert selected.timestamp == datetime(2020, 7, 1, tzinfo=UTC)


def test_does_not_substitute_adjacent_year_capture() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)

    assert select_annual_capture([capture("2019-12-31T23:59:59+00:00")], target) is None


def test_tie_breaker_prefers_earlier_capture() -> None:
    target = datetime(2020, 6, 30, 12, tzinfo=UTC)
    captures = [
        capture("2020-07-01T12:00:00+00:00"),
        capture("2020-06-29T12:00:00+00:00"),
    ]

    ranked = rank_annual_captures(captures, target)

    assert ranked[0].timestamp == datetime(2020, 6, 29, 12, tzinfo=UTC)
