from org_auth_part1.extract import extract_page_text


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


def test_normalizes_carriage_returns_in_extracted_text() -> None:
    result = extract_page_text(
        "<main><p>First line\r\nSecond line\rThird line</p></main>",
        minimum_words=1,
    )

    assert "\r" not in result.page_text_clean
