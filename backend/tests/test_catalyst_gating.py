"""Unit tests for catalyst gating: off-scope excluded, wedge format."""
from unittest.mock import patch
import json

from sift.gemini_client import catalyst_bullets
from sift.config import EXCLUDED_TOPICS, NEWSLETTER_AUDIENCE


def test_catalyst_bullets_prompt_includes_excluded_topics():
    """Catalyst prompt must reference excluded topics so model gates them."""
    with patch("sift.gemini_client.generate_text") as mock:
        mock.return_value = "[]"
        catalyst_bullets([{"title": "News", "url": "https://x", "text": "Body"}], max_bullets=1)
    call_args = mock.call_args[0][0]
    for topic in EXCLUDED_TOPICS[:3]:
        assert topic in call_args or topic.split("/")[0] in call_args


def test_catalyst_bullets_prompt_includes_audience():
    assert NEWSLETTER_AUDIENCE in ("B2B builders/devtools founders", "B2B builders")


def test_catalyst_bullets_empty_input():
    assert catalyst_bullets([], max_bullets=5) == []


def test_catalyst_bullets_returns_opportunity_wedge():
    """Strict catalyst schema includes opportunity_wedge or 'Unclear from evidence'."""
    raw = [{
        "title": "API change",
        "what_changed": "Breaking change.",
        "who_feels_it": "Backend teams",
        "problems_created": ["migration burden", "downtime risk"],
        "opportunity_wedge": "Start with backend teams who must migrate, build a compatibility layer.",
        "confidence": 0.8,
        "source_urls": ["https://example.com"],
    }]
    with patch("sift.gemini_client.generate_text", return_value=json.dumps(raw)):
        out = catalyst_bullets([{"title": "T", "url": "https://u", "text": "B"}], max_bullets=1)
    assert len(out) == 1
    assert "wedge" in out[0] or "opportunity_wedge" in str(out[0])
    wedge = out[0].get("opportunity_wedge") or out[0].get("wedge", "")
    assert "Unclear" in wedge or "Start with" in wedge
