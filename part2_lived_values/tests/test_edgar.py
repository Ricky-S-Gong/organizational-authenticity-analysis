from org_auth_part2.edgar import filing_document_url, normalize_ticker, select_def14a_for_year


def test_normalize_ticker_handles_sec_dash_style() -> None:
    assert normalize_ticker("BRK.B") == "BRK-B"


def test_filing_document_url() -> None:
    assert (
        filing_document_url("0000320193", "0001308179-24-000010", "laap2024_def14a.htm")
        == "https://www.sec.gov/Archives/edgar/data/320193/000130817924000010/laap2024_def14a.htm"
    )


def test_select_def14a_for_year_prefers_def14a() -> None:
    submissions = {
        "filings": {
            "recent": {
                "accessionNumber": ["0001", "0002", "0003"],
                "filingDate": ["2024-04-01", "2024-03-01", "2023-03-01"],
                "reportDate": ["2024-04-01", "2024-03-01", "2023-03-01"],
                "form": ["DEFA14A", "DEF 14A", "DEF 14A"],
                "primaryDocument": ["supp.htm", "main.htm", "old.htm"],
            }
        }
    }
    selected = select_def14a_for_year(
        ticker="AAPL",
        cik="0000320193",
        company_name="Apple",
        year=2024,
        submissions=submissions,
        include_supplements=True,
    )
    assert selected is not None
    assert selected.form == "DEF 14A"
    assert selected.primary_document == "main.htm"


def test_select_def14a_returns_none_for_missing_year() -> None:
    submissions = {
        "filings": {
            "recent": {
                "accessionNumber": ["0003"],
                "filingDate": ["2023-03-01"],
                "reportDate": ["2023-03-01"],
                "form": ["DEF 14A"],
                "primaryDocument": ["old.htm"],
            }
        }
    }
    assert (
        select_def14a_for_year(
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple",
            year=2024,
            submissions=submissions,
        )
        is None
    )
