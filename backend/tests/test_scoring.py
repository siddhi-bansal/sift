"""Unit tests for filter thresholds and unmet_score behavior."""
from unmet.analyze.scoring import (
    noise_penalty,
    passes_candidate_filter,
    unmet_score,
    filter_and_rank_candidates,
)


def test_passes_candidate_filter_pain_high_scores():
    assert passes_candidate_filter("PAIN", 0.7, 0.6, 0.5, 0.6) is True


def test_passes_candidate_filter_fails_other_label():
    assert passes_candidate_filter("OTHER", 0.9, 0.9, 0.9, 0.9) is False


def test_passes_candidate_filter_fails_low_audience_fit():
    assert passes_candidate_filter("PAIN", 0.5, 0.8, 0.8, 0.8) is False


def test_passes_candidate_filter_fails_low_pain_and_actionability():
    assert passes_candidate_filter("PAIN", 0.7, 0.3, 0.4, 0.6) is False


def test_passes_candidate_filter_actionability_alt():
    assert passes_candidate_filter("PAIN", 0.7, 0.4, 0.65, 0.6) is True


def test_noise_penalty_show_hn_non_pain():
    item = {"title": "Show HN: My side project", "exclude_reason": None}
    p = noise_penalty(item, "NEWS", "hn", [])
    assert p >= 0.25


def test_noise_penalty_exclude_reason():
    item = {"title": "Foo", "exclude_reason": "off-scope"}
    p = noise_penalty(item, "PAIN", "hn", ["pain quote"])
    assert p >= 0.20


def test_unmet_score_formula():
    s = unmet_score(0.4, 0.5, 0.6, 0.7, 0.0)
    expected = 0.35 * 0.4 + 0.30 * 0.5 + 0.25 * 0.6 + 0.10 * 0.7
    assert abs(s - expected) < 0.001


def test_filter_and_rank_candidates_top_n():
    items = [
        {"id": "a", "title": "A", "url": "https://a", "source": "hn"},
        {"id": "b", "title": "B", "url": "https://b", "source": "hn"},
    ]
    labels_map = {
        "a": {"label": "PAIN", "confidence": 0.8, "audience_fit": 0.8, "pain_intensity": 0.8, "actionability": 0.7, "evidence_spans": [], "exclude_reason": None},
        "b": {"label": "PAIN", "confidence": 0.7, "audience_fit": 0.7, "pain_intensity": 0.6, "actionability": 0.6, "evidence_spans": [], "exclude_reason": None},
    }
    out = filter_and_rank_candidates(items, labels_map, top_n=1)
    assert len(out) == 1
    assert out[0]["id"] == "a" or out[0]["id"] == "b"
