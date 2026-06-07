from org_auth_part2.extract import extract_visible_text, extraction_quality


def test_extract_visible_text_removes_script_and_style() -> None:
    html = b"""
    <html><head><style>.x{}</style><script>alert(1)</script></head>
    <body><h1>Proxy Statement</h1><p>Shareholders vote on directors.</p></body></html>
    """
    text = extract_visible_text(html, "text/html")
    assert "Proxy Statement" in text
    assert "Shareholders vote on directors" in text
    assert "alert" not in text


def test_extraction_quality_codes_short_text() -> None:
    assert extraction_quality("") == "empty"
    assert extraction_quality("short text", minimum_words=10) == "insufficient_text"
