from __future__ import annotations

from org_auth_part4.sections import classify_section, parse_proxy_sections, section_records_for_row


def test_classify_section_known_families() -> None:
    assert classify_section("Compensation Discussion and Analysis") == "compensation"
    assert classify_section("Information About the Annual Meeting") == "meeting_voting"
    assert classify_section("Human Capital and Diversity") == "human_capital_values"


def test_parse_proxy_sections_detects_heading_spans() -> None:
    text = """
    CORPORATE GOVERNANCE
    Our board of directors oversees governance and leadership matters for shareholders.
    The committee reviews independence and accountability practices for the company.
    Directors discuss risk oversight, corporate governance guidelines, responsible leadership,
    committee charters, and shareholder engagement throughout the year.

    COMPENSATION DISCUSSION AND ANALYSIS
    Executive compensation is designed to support performance and long-term value.
    The compensation committee reviews incentive plan outcomes and leadership.
    Pay decisions connect annual incentives, equity awards, accountability, and financial
    performance for senior executives and other leaders.

    HUMAN CAPITAL
    Employees, diversity, inclusion, safety, and workplace culture are priorities.
    Our workforce programs support talent and professional development.
    The company invests in employee engagement, health, wellbeing, belonging, community, and
    career development for our people.

    INFORMATION ABOUT THE ANNUAL MEETING
    Shareholders may vote by proxy card. A quorum is required for the annual meeting.
    Beneficial owners, record date rules, voting instructions, proposals, and proxy materials are
    described for shareholders attending the meeting.
    """
    sections = parse_proxy_sections(text)
    families = {section.family for section in sections}
    expected = {"governance_board", "compensation", "human_capital_values", "meeting_voting"}
    assert expected <= families


def test_section_records_include_theme_and_genre_counts() -> None:
    row = {
        "ticker": "TST",
        "company_name": "Test Co",
        "sector": "Technology",
        "year": 2024,
        "word_count": 100,
        "page_text_clean": """
        HUMAN CAPITAL
        Employees and workplace safety matter to our workforce and our people.
        INFORMATION ABOUT THE ANNUAL MEETING
        Shareholders may vote by proxy card at the annual meeting.
        """,
    }
    records = section_records_for_row(row)
    assert records
    assert any(record["section_genre_count"] > 0 for record in records)
    assert any(record["total_theme_matches"] > 0 for record in records)
