"""Evidence-topic coherence: validate that cluster title/topic is supported by evidence snippets."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Direct indicators: one hit is enough to pass coherence
DIRECT_INDICATORS = {
    "sql injection",
    "hardcoded key",
    "vulnerability",
    "vulnerabilities",
    "exploit",
    "prompt injection",
    "xss",
    "rce",
    "data breach",
    "security patch",
    "cve",
    "zero day",
    "auth bypass",
    "secret leak",
}


def _snippet_keyword_hits(snippets: list[str], topic_tags: list[str]) -> int:
    """Count snippet hits: how many snippets contain at least one topic_tag (case-insensitive word match)."""
    if not topic_tags or not snippets:
        return 0
    tag_set = {t.strip().lower() for t in topic_tags if t and t.strip()}
    hits = 0
    for s in (snippets or []):
        lower = (s or "").lower()
        for tag in tag_set:
            # Word boundary style: tag as whole word or as substring for multi-word tags
            if tag in lower:
                hits += 1
                break
    return hits


def _direct_indicator_hits(snippets: list[str]) -> int:
    """Count how many snippets contain any direct indicator."""
    if not snippets:
        return 0
    combined = " ".join((s or "").lower() for s in snippets)
    return sum(1 for ind in DIRECT_INDICATORS if ind in combined)


def validate_topic_coherence(
    title: str,
    topic_tags: list[str],
    evidence_snippets: list[str],
) -> tuple[bool, str]:
    """
    Validate that the cluster title/topic is supported by evidence snippets.
    Requires: >=2 snippet keyword hits across topic_tags OR >=1 direct indicator hit.
    Returns (passed: bool, reason: str).
    """
    snippet_hits = _snippet_keyword_hits(evidence_snippets, topic_tags)
    direct_hits = _direct_indicator_hits(evidence_snippets or [])

    if direct_hits >= 1:
        return (True, f"direct_indicator_hits={direct_hits}")
    if snippet_hits >= 2:
        return (True, f"snippet_keyword_hits={snippet_hits} across topic_tags")
    return (
        False,
        f"insufficient support: snippet_keyword_hits={snippet_hits} (need >=2), direct_indicator_hits={direct_hits} (need >=1)",
    )
