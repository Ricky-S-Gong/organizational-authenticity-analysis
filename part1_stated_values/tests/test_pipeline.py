from org_auth_part1.pipeline import build_final_rows, build_text_artifacts


def test_build_text_artifacts_extracts_fetched_html() -> None:
    status = [{"ticker": "MSFT", "year": "2024"}]
    fetches = {
        ("MSFT", 2024): {
            "fetch_status": "success",
            "content": (
                b"<main><h1>Our mission</h1>"
                b"<p>We serve customers with integrity and innovation.</p></main>"
            ),
        }
    }

    artifacts = build_text_artifacts(status, fetches)

    assert len(artifacts) == 1
    assert "integrity" in artifacts[0]["page_text_clean"]


def test_final_rows_keep_explicit_gap_reason() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "no_cdx_capture",
            "failure_reason": "no same-year CDX capture",
            "selected_original_url": "",
            "selected_replay_url": "",
            "selected_capture_timestamp": "",
        }
    ]

    rows = build_final_rows(status, [], {})

    assert rows[0]["observation_status"] == "no_cdx_capture"
    assert rows[0]["gap_reason"] == "no same-year CDX capture"
    assert rows[0]["changed_from_prior"] is None


def test_failed_fetch_is_preserved_as_text_artifact() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_original_url": "https://example.com/about",
            "selected_replay_url": "https://web.archive.org/example",
            "selected_capture_timestamp": "2024-06-30T12:00:00+00:00",
        }
    ]
    fetches = {
        ("MSFT", 2024): {
            "fetch_status": "failed",
            "error": "HTTPStatusError: 503 Service Unavailable",
        }
    }

    artifacts = build_text_artifacts(status, fetches)
    rows = build_final_rows(status, artifacts, fetches)

    assert len(artifacts) == 1
    assert artifacts[0]["fetch_status"] == "failed"
    assert "retrieval_failed" in artifacts[0]["qa_flags"]
    assert rows[0]["observation_status"] == "retrieval_failed"
    assert "503" in rows[0]["gap_reason"]


def test_short_extraction_is_not_marked_usable() -> None:
    status = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "sector": "Technology",
            "year": "2024",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_original_url": "https://example.com/about",
            "selected_replay_url": "https://web.archive.org/example",
            "selected_capture_timestamp": "2024-06-30T12:00:00+00:00",
        }
    ]
    fetches = {("MSFT", 2024): {"fetch_status": "success", "content": b"<main>Short</main>"}}
    artifacts = build_text_artifacts(status, fetches)

    rows = build_final_rows(status, artifacts, fetches)

    assert rows[0]["observation_status"] == "insufficient_substantive_text"
