"""Unit tests for dedupe across sections (used_urls)."""


def test_dedupe_used_urls_logic():
    """When building report, a URL used in pain section must not be reused in catalyst."""
    used_urls = set()
    pain_links = ["https://a.com", "https://b.com"]
    for u in pain_links:
        used_urls.add(u)
    catalyst_source_urls = ["https://a.com", "https://c.com"]
    # Catalyst with url already in used_urls should be skipped (caller logic)
    allowed = [u for u in catalyst_source_urls if u not in used_urls]
    assert "https://a.com" not in allowed
    assert "https://c.com" in allowed


def test_dedupe_same_url_not_in_both_sections():
    """Same URL cannot appear in both pain and catalyst sections."""
    used = set()
    pain_urls = ["https://hn.com/item?id=1"]
    catalyst_candidates = [
        {"source_urls": ["https://hn.com/item?id=1"]},
        {"source_urls": ["https://other.com"]},
    ]
    for u in pain_urls:
        used.add(u)
    included_catalysts = []
    for cat in catalyst_candidates:
        surls = cat.get("source_urls") or []
        if any(u in used for u in surls if u):
            continue
        included_catalysts.append(cat)
        for u in surls:
            used.add(u)
    assert len(included_catalysts) == 1
    assert included_catalysts[0]["source_urls"] == ["https://other.com"]
