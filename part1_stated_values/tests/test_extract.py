from org_auth_part1.extract import extract_json_text, extract_page_text


def test_extracts_main_text_and_removes_boilerplate_and_invisible_content() -> None:
    html = """
    <html>
      <head><style>hidden style</style><script>hidden script</script></head>
      <body>
        <header><a href="/">Home</a><a href="/about">About</a></header>
        <main>
          <h1>Our purpose</h1>
          <p>We build trusted products that help communities thrive.</p>
          <section><p>Integrity and service guide every decision we make.</p></section>
        </main>
        <footer>Privacy Terms Careers</footer>
      </body>
    </html>
    """

    result = extract_page_text(html, minimum_words=5)

    assert result.used_main_region is True
    assert "Our purpose" in result.page_text_clean
    assert "Integrity and service" in result.page_text_clean
    assert "Home" in result.visible_text_raw
    assert "Home" not in result.page_text_clean
    assert "Privacy Terms" not in result.page_text_clean
    assert "hidden script" not in result.visible_text_raw
    assert result.qa_flags == ()


def test_removes_class_based_cookie_and_navigation_boilerplate() -> None:
    html = """
    <body>
      <div class="cookie-banner">Accept every cookie</div>
      <div id="sidebar-menu">Products Investors Careers</div>
      <div>
        <p>Our company acts with integrity and puts customers first.</p>
        <p>We invest in employees, communities, and sustainable innovation.</p>
      </div>
    </body>
    """

    result = extract_page_text(html, minimum_words=5)

    assert "Accept every cookie" not in result.page_text_clean
    assert "Products Investors Careers" not in result.page_text_clean
    assert "puts customers first" in result.page_text_clean
    assert "no_main_region" in result.qa_flags


def test_flags_short_error_page_instead_of_silently_accepting_it() -> None:
    result = extract_page_text("<main><h1>404 Page not found</h1></main>")

    assert result.page_text_clean == "404 Page not found"
    assert "short_text" in result.qa_flags
    assert "likely_error_page" in result.qa_flags


def test_flags_link_heavy_page_for_manual_review() -> None:
    links = "".join(f'<a href="/{number}">Navigation item {number}</a>' for number in range(20))
    html = f"<body>{links}<p>Small company description.</p></body>"
    result = extract_page_text(html, minimum_words=2)

    assert "high_link_text_ratio" in result.qa_flags


def test_void_elements_do_not_leak_main_region_to_later_content() -> None:
    html = """
    <body>
      <main><p>Our values<br>Integrity and service</p></main>
      <section><p>Unrelated content after main.</p></section>
    </body>
    """

    result = extract_page_text(html, minimum_words=2)

    assert "Integrity and service" in result.page_text_clean
    assert "Unrelated content" not in result.page_text_clean


def test_unclosed_wbr_does_not_corrupt_boilerplate_stack() -> None:
    html = """
    <body>
      <header><nav><a href="/about">About</a></nav></header>
      <div>
        <h1>About <wbr>UnitedHealth Group</h1>
        <p>We help people live healthier lives and make the health system work better.</p>
        <p>Our teams use clinical insight, technology, data, and information to serve people.</p>
      </div>
    </body>
    """

    result = extract_page_text(html, minimum_words=10)

    assert "make the health system work better" in result.page_text_clean
    assert "clinical insight" in result.page_text_clean
    assert "About UnitedHealth Group" in result.page_text_clean


def test_body_start_resets_pre_body_navigation_stack() -> None:
    html = """
    <html>
      <div class="navbar"><a href="/investors">Investors</a>
      <body>
        <div>
          <p>Our mission is to help people live healthier lives.</p>
          <p>We use technology, data, service, and clinical insight to improve care.</p>
        </div>
      </body>
    </html>
    """

    result = extract_page_text(html, minimum_words=10)

    assert "help people live healthier lives" in result.page_text_clean
    assert "clinical insight" in result.page_text_clean
    assert "Investors" not in result.page_text_clean


def test_full_page_aspnet_form_does_not_hide_main_content() -> None:
    html = """
    <body>
      <form id="mainform">
        <div>
          <p>We are committed to introducing innovative approaches and services.</p>
          <p>Our clinical insight and technology help people live healthier lives.</p>
        </div>
      </form>
    </body>
    """

    result = extract_page_text(html, minimum_words=10)

    assert "innovative approaches" in result.page_text_clean
    assert "clinical insight" in result.page_text_clean


def test_normalizes_carriage_returns_in_extracted_text() -> None:
    result = extract_page_text(
        "<main><p>First line\r\nSecond line\rThird line</p></main>",
        minimum_words=1,
    )

    assert "\r" not in result.page_text_clean


def test_trafilatura_fallback_requires_explicit_flag(monkeypatch) -> None:
    def fallback(*args, **kwargs):
        return "Our mission is to serve customers with integrity and innovation."

    monkeypatch.setattr("org_auth_part1.extract.trafilatura.extract", fallback)

    result = extract_page_text("<body><nav>Menu</nav><div>Hi</div></body>")

    assert result.page_text_clean == "Hi"
    assert "trafilatura_fallback" not in result.qa_flags
    assert result.extraction_backend == "htmlparser"


def test_trafilatura_fallback_can_rescue_short_primary_text(monkeypatch) -> None:
    def fallback(*args, **kwargs):
        return "Our mission is to serve customers with integrity and innovation."

    monkeypatch.setattr("org_auth_part1.extract.trafilatura.extract", fallback)

    result = extract_page_text(
        "<body><nav>Menu</nav><div>Hi</div></body>",
        enable_trafilatura_fallback=True,
    )

    assert "serve customers" in result.page_text_clean
    assert "trafilatura_fallback" in result.qa_flags
    assert result.extraction_backend == "htmlparser+trafilatura"


def test_trafilatura_fallback_tries_recall_after_precision_is_empty(monkeypatch) -> None:
    calls = []

    def fallback(*args, **kwargs):
        calls.append(kwargs)
        if kwargs.get("favor_recall"):
            return (
                "In 1999 NVIDIA sparked the growth of the PC gaming market and redefined "
                "modern computer graphics. GPU deep learning ignited modern AI and helps "
                "computers, robots, and self-driving cars perceive the world."
            )
        return ""

    monkeypatch.setattr("org_auth_part1.extract.trafilatura.extract", fallback)

    result = extract_page_text(
        "<body><nav>CONTACT US</nav><div>Get answers to support questions.</div></body>",
        enable_trafilatura_fallback=True,
    )

    assert "modern computer graphics" in result.page_text_clean
    assert result.clean_word_count >= 25
    assert result.extraction_backend == "htmlparser+trafilatura"
    assert calls[0]["favor_precision"] is True
    assert calls[1]["favor_recall"] is True


def test_extract_json_text_keeps_narrative_and_skips_asset_fields() -> None:
    payload = {
        "data": {
            "title": "WELCOME TO NIKE, INC.",
            "image": {
                "src": "https://cdn.example.com/image.jpg",
                "alt": "Nike campus exterior",
                "width": 1200,
            },
            "intro": "<p>We champion athletes and sport through innovation and purpose.</p>",
            "blocks": [
                {"body": "Our teams serve communities with creativity, inclusion, and integrity."},
                {"href": "https://example.com/news"},
            ],
        }
    }

    text = extract_json_text(payload)

    assert "champion athletes" in text
    assert "serve communities" in text
    assert "cdn.example.com" not in text
