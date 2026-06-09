def test_parse_page_count_caps_at_five():
    from backend.routes.outline_routes import _parse_page_count

    assert _parse_page_count(10) == 5
    assert _parse_page_count("8") == 5
    assert _parse_page_count(5) == 5
    assert _parse_page_count(1) == 2
    assert _parse_page_count("") is None
