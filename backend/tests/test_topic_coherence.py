"""Unit tests for evidence-topic coherence: validate_topic_coherence, mismatch fails."""
from sift.analyze.topic_coherence import validate_topic_coherence


def test_validate_topic_coherence_pass_two_snippet_hits():
    """>=2 snippet keyword hits across topic_tags passes."""
    passed, reason = validate_topic_coherence(
        title="Dev tooling pain",
        topic_tags=["dev", "tooling", "pain"],
        evidence_snippets=[
            "Developers hate the dev workflow",
            "Tooling is broken and nobody fixes it",
        ],
    )
    assert passed is True
    assert "snippet_keyword_hits" in reason or "direct_indicator" in reason


def test_validate_topic_coherence_pass_direct_indicator():
    """>=1 direct indicator (e.g. vulnerability) passes."""
    passed, reason = validate_topic_coherence(
        title="Security update",
        topic_tags=["security"],
        evidence_snippets=["New vulnerability found in library X"],
    )
    assert passed is True
    assert "direct_indicator" in reason


def test_validate_topic_coherence_fail_mismatched_hn_item():
    """Mismatched HN item: title/topic not supported by snippets fails coherence."""
    # Topic suggests "Kubernetes" but snippets say nothing about k8s
    passed, reason = validate_topic_coherence(
        title="Kubernetes operators are hard",
        topic_tags=["kubernetes", "operators"],
        evidence_snippets=[
            "I love my cat",
            "The weather is nice today",
        ],
    )
    assert passed is False
    assert "insufficient" in reason.lower() or "snippet_keyword_hits=0" in reason or "need" in reason.lower()


def test_validate_topic_coherence_fail_only_one_hit():
    """Only 1 snippet keyword hit (need >=2) and no direct indicator fails."""
    passed, reason = validate_topic_coherence(
        title="Dev pain",
        topic_tags=["dev", "pain"],
        evidence_snippets=[
            "Developers are frustrated",  # one hit on "dev"
            "The coffee machine is broken",  # no tag hit
        ],
    )
    assert passed is False
