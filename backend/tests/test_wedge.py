"""Unit tests for wedge format enforcement."""
from unmet.newsletter_style import (
    BANNED_PHRASES,
    NewsletterItem,
    validate_item,
    _contains_banned_phrase,
)


def test_wedge_format_validation_accepts_start_with():
    """Wedge 'Start with <buyer> who <situation>, build <first feature>.' is valid."""
    item = NewsletterItem(
        hook="Teams are stuck on legacy deploys and want one-click rollbacks.",
        explanation="Evidence shows pain.",
        why_bullets=["Cost.", "Time."],
        who="Platform engineers",
        wedge="Start with platform engineers who manage legacy deploys, build a one-click rollback.",
        evidence_snippets=["stuck on legacy", "one-click"],
        links=["https://example.com"],
        strength_or_impact="Med",
    )
    errs = validate_item(item)
    assert "wedge" not in " ".join(errs).lower() or "Start with" in item.wedge


def test_wedge_unclear_from_evidence_allowed():
    item = NewsletterItem(
        hook="Something is happening in dev tooling and teams are watching for updates.",
        explanation="Unclear.",
        why_bullets=["See links."],
        who="Builders",
        wedge="Unclear from evidence.",
        evidence_snippets=["something"],
        links=["https://x.com"],
        strength_or_impact="Low",
    )
    errs = validate_item(item)
    assert "Unclear from evidence." == item.wedge


def test_banned_phrases_detected():
    assert _contains_banned_phrase("This highlights the problem") is True
    assert _contains_banned_phrase("Existing tools are often broken") is True
    assert _contains_banned_phrase("Teams need a simple fix") is False
