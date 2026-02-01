#!/usr/bin/env python3
"""
Run backend tests without relying on pytest's plugin system.
Use this if pytest fails with ImportError (e.g. hydra/omegaconf conflict in system Python).
Usage: python run_tests.py
"""
import sys


def run_scoring_tests():
    from sift.analyze.scoring import (
        filter_and_rank_candidates,
        noise_penalty,
        passes_candidate_filter,
        sift_score,
    )

    assert passes_candidate_filter("PAIN", 0.7, 0.6, 0.5, 0.6) is True
    assert passes_candidate_filter("OTHER", 0.9, 0.9, 0.9, 0.9) is False
    assert passes_candidate_filter("PAIN", 0.5, 0.8, 0.8, 0.8) is False
    assert passes_candidate_filter("PAIN", 0.7, 0.3, 0.4, 0.6) is False
    assert passes_candidate_filter("PAIN", 0.7, 0.4, 0.65, 0.6) is True

    item = {"title": "Show HN: My side project", "exclude_reason": None}
    assert noise_penalty(item, "NEWS", "hn", []) >= 0.25
    item2 = {"title": "Foo", "exclude_reason": "off-scope"}
    assert noise_penalty(item2, "PAIN", "hn", ["pain quote"]) >= 0.20

    s = sift_score(0.4, 0.5, 0.6, 0.7, 0.0)
    expected = 0.35 * 0.4 + 0.30 * 0.5 + 0.25 * 0.6 + 0.10 * 0.7
    assert abs(s - expected) < 0.001

    items = [
        {"id": "a", "title": "A", "url": "https://a", "source": "hn"},
        {"id": "b", "title": "B", "url": "https://b", "source": "hn"},
    ]
    labels_map = {
        "a": {
            "label": "PAIN",
            "confidence": 0.8,
            "audience_fit": 0.8,
            "pain_intensity": 0.8,
            "actionability": 0.7,
            "evidence_spans": [],
            "exclude_reason": None,
        },
        "b": {
            "label": "PAIN",
            "confidence": 0.7,
            "audience_fit": 0.7,
            "pain_intensity": 0.6,
            "actionability": 0.6,
            "evidence_spans": [],
            "exclude_reason": None,
        },
    }
    out = filter_and_rank_candidates(items, labels_map, top_n=1)
    assert len(out) == 1
    assert out[0]["id"] in ("a", "b")
    assert "sift_score" in out[0]


def run_newsletter_style_tests():
    from sift.newsletter_style import BANNED_PHRASES, get_intro

    intro = get_intro()
    assert "Sift" in intro and "Sift scans" in intro
    assert len(BANNED_PHRASES) >= 1


def main():
    print("Running backend tests (no pytest)...")
    run_scoring_tests()
    print("  scoring: OK")
    run_newsletter_style_tests()
    print("  newsletter_style: OK")
    print("All run_tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
