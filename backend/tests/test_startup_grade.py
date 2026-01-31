"""Tests for startup-grade card schema and validation."""
from unmet.newsletter_style import (
    validate_startup_grade_card,
    validate_startup_grade_card_split,
    STARTUP_GRADE_BANNED_PHRASES,
)


def _valid_card() -> dict:
    return {
        "title": "One compromised maintainer infects downstream projects",
        "hook": "Supply chain attacks are rising and maintainers rarely have tooling to prove integrity.",
        "problem": "Open-source maintainers who ship widely used deps are blocked from proving integrity because tooling is fragmented.",
        "evidence": ["supply chain attacks rising", "maintainers rarely have tooling", "prove integrity"],
        "who_pays": "Security leads at companies with large OSS dependency trees",
        "stakes": ["One poisoned release can take down production", "Compliance requires attestation"],
        "why_now": ["SBOM mandates are creating demand", "Adoption of sigstore is growing"],
        "wedge": {
            "icp": "Start with security leads at Series B+ who ship OSS deps",
            "mvp": "CLI that emits a signed attestation for a repo in under a week",
            "why_they_pay": "Reduced audit time and compliance proof",
            "first_channel": "Security / platform eng Slack communities",
            "anti_feature": "No full SBOM generation at first",
        },
        "confidence": "med",
        "kill_criteria": "If no team pays for attestation in 10 outbound conversations, drop.",
    }


def test_validate_startup_grade_card_accepts_valid():
    card = _valid_card()
    errs = validate_startup_grade_card(card)
    assert errs == [], errs


def test_validate_startup_grade_card_rejects_missing_who_pays():
    card = _valid_card()
    card["who_pays"] = ""
    errs = validate_startup_grade_card(card)
    assert any("who_pays" in e for e in errs)


def test_validate_startup_grade_card_rejects_generic_who_pays():
    card = _valid_card()
    card["who_pays"] = "developers"
    errs = validate_startup_grade_card(card)
    assert any("who_pays" in e or "role" in e for e in errs)


def test_validate_startup_grade_card_rejects_missing_mvp_artifact():
    card = _valid_card()
    card["wedge"] = {**card["wedge"], "mvp": "Improve support and make it better"}
    errs = validate_startup_grade_card(card)
    assert any("mvp" in e or "tangible" in e for e in errs)


def test_validate_startup_grade_card_rejects_empty_kill_criteria():
    card = _valid_card()
    card["kill_criteria"] = ""
    errs = validate_startup_grade_card(card)
    assert any("kill_criteria" in e for e in errs)


def test_validate_startup_grade_card_rejects_domain_only_title():
    card = _valid_card()
    card["title"] = "Software Supply Chain Vulnerabilities"
    errs = validate_startup_grade_card(card)
    assert any("failure" in e or "title" in e for e in errs)


def test_validate_startup_grade_card_accepts_failure_mode_title():
    card = _valid_card()
    card["title"] = "Platform policy shifts can break CSPs overnight"
    errs = validate_startup_grade_card(card)
    assert not any("failure" in e for e in errs), errs


def test_validate_startup_grade_card_rejects_banned_phrase():
    card = _valid_card()
    card["problem"] = "This highlights the need for robust tooling."
    errs = validate_startup_grade_card(card)
    assert any("banned" in e for e in errs)


def test_validate_startup_grade_card_accepts_evidence_objects():
    """Evidence can be list of objects with quote, post_url, comment_url (forensic links)."""
    card = _valid_card()
    card["evidence"] = [
        {"quote": "supply chain attacks rising", "post_url": "https://news.ycombinator.com/item?id=123", "comment_url": "https://news.ycombinator.com/item?id=456"},
        {"quote": "maintainers rarely have tooling", "post_url": "https://news.ycombinator.com/item?id=123", "comment_url": None},
    ]
    errs = validate_startup_grade_card(card)
    assert errs == [], errs


def test_evidence_comment_permalink_ratio_at_least_70_percent():
    """Sanity check: when generating cards, at least 70% of evidence bullets should include a comment permalink; ratio helper is used for auto-downgrade."""
    from unmet.gemini_client import _evidence_comment_permalink_ratio, EVIDENCE_COMMENT_PERMALINK_MIN_RATIO

    # 3/4 = 75% with comment_url -> above threshold
    evidence_ok = [
        {"quote": "a", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": "https://news.ycombinator.com/item?id=10"},
        {"quote": "b", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": "https://news.ycombinator.com/item?id=11"},
        {"quote": "c", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": "https://news.ycombinator.com/item?id=12"},
        {"quote": "d", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": None},
    ]
    assert _evidence_comment_permalink_ratio(evidence_ok) >= EVIDENCE_COMMENT_PERMALINK_MIN_RATIO

    # 1/3 with comment_url -> below 70%; generator should auto-downgrade confidence
    evidence_weak = [
        {"quote": "a", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": "https://news.ycombinator.com/item?id=10"},
        {"quote": "b", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": None},
        {"quote": "c", "post_url": "https://news.ycombinator.com/item?id=1", "comment_url": None},
    ]
    assert _evidence_comment_permalink_ratio(evidence_weak) < EVIDENCE_COMMENT_PERMALINK_MIN_RATIO


def test_validate_accepts_proxy_stakes():
    """Card with proxy/estimate stakes (no monetary) should pass stakes rule (time/reliability/security/money)."""
    card = _valid_card()
    card["stakes"] = [
        "Estimate: 2–4 engineer-hours per incident (MTTR impact).",
        "Proxy: likely sev escalation if unaddressed.",
    ]
    hard, soft, _ = validate_startup_grade_card_split(card)
    assert not any("stakes" in e for e in hard), hard
    assert not any("stakes" in e for e in soft), soft
    errs = validate_startup_grade_card(card)
    assert not any("stakes" in e for e in errs), errs
