"""Unit tests for classify_and_score_item JSON parsing and fallback."""
import json
from unittest.mock import patch

import pytest

from unmet.gemini_client import classify_and_score_item, classify_pain_label


def test_classify_and_score_item_valid_json():
    """Valid JSON is parsed and returned with correct types."""
    raw = {
        "label": "PAIN",
        "confidence": 0.8,
        "audience_fit": 0.7,
        "pain_intensity": 0.9,
        "actionability": 0.6,
        "evidence_spans": ["I can't get this to work", "blocked for hours"],
        "topic_tags": ["devtools", "pain"],
        "claim_anchors": ["blocked for hours"],
        "exclude_reason": None,
    }
    with patch("unmet.gemini_client.generate_text", return_value=json.dumps(raw)):
        out = classify_and_score_item("body", "title")
    assert out["label"] == "PAIN"
    assert out["confidence"] == 0.8
    assert out["evidence_spans"] == ["I can't get this to work", "blocked for hours"]
    assert out["topic_tags"] == ["devtools", "pain"]
    assert out["claim_anchors"] == ["blocked for hours"]
    assert out["exclude_reason"] is None


def test_classify_and_score_item_json_with_markdown_wrapper():
    """JSON wrapped in ```json ... ``` is stripped and parsed."""
    raw = {"label": "DISCUSSION", "confidence": 0.6, "audience_fit": 0.5, "pain_intensity": 0.4, "actionability": 0.5, "evidence_spans": [], "exclude_reason": None}
    with patch("unmet.gemini_client.generate_text", return_value="```json\n" + json.dumps(raw) + "\n```"):
        out = classify_and_score_item("body", "title")
    assert out["label"] == "DISCUSSION"
    assert out["confidence"] == 0.6


def test_classify_and_score_item_parse_fallback():
    """On JSON parse failure, fall back to classify_pain_label and default scores."""
    with patch("unmet.gemini_client.generate_text", return_value="PAIN\n0.7"):
        with patch("unmet.gemini_client.classify_pain_label", return_value=("PAIN", 0.7)):
            out = classify_and_score_item("body", "title")
    # Fallback path: we get label/confidence from classify_pain_label, rest default
    assert out["label"] == "PAIN"
    assert out["confidence"] == 0.7
    assert out["audience_fit"] == 0.0
    assert out["pain_intensity"] == 0.0
    assert out["actionability"] == 0.0
    assert out["evidence_spans"] == []
    assert out["topic_tags"] == []
    assert out["claim_anchors"] == []
    assert out["exclude_reason"] == "parse_fallback"


def test_classify_and_score_item_invalid_json_triggers_fallback():
    """Invalid JSON triggers fallback to two-line classifier."""
    with patch("unmet.gemini_client.generate_text", return_value="not valid json at all"):
        with patch("unmet.gemini_client.classify_pain_label", return_value=("OTHER", 0.0)):
            out = classify_and_score_item("body", "title")
    assert out["label"] == "OTHER"
    assert out["exclude_reason"] == "parse_fallback"
