"""Extract 2–4 short evidence snippets with pain language from item title + text + HN comments."""
from __future__ import annotations

import re
from typing import Any

PAIN_WORDS = {
    "blocked", "locked", "can't", "cannot", "failed", "billing", "support",
    "hate", "frustrat", "broken", "sucks", "worst", "wish", "need",
    "stuck", "unusable", "terrible", "annoy", "struggl", "problem", "issue",
    "bug", "please fix", "please add", "why can't", "how do i", "recommend",
}
MAX_SNIPPET_WORDS = 12
MAX_SNIPPETS = 4


def _extract_sentences(text: str) -> list[str]:
    """Split into rough sentences (period, newline, or long comma)."""
    if not text or not text.strip():
        return []
    text = text.replace("\n", ". ")
    parts = re.split(r"[.!?]\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 10]


def _contains_pain(s: str) -> bool:
    lower = s.lower()
    return any(w in lower for w in PAIN_WORDS)


def _first_n_words(s: str, n: int = MAX_SNIPPET_WORDS) -> str:
    words = s.split()[:n]
    return " ".join(words).strip()


def extract_evidence_snippets(item: dict[str, Any], max_snippets: int = MAX_SNIPPETS) -> list[str]:
    """
    For a pain candidate item (title, text, metadata.comments), extract 2–4 short snippets
    that contain pain language. Each snippet ≤12 words. Prefer title if it has pain language.
    """
    snippets: list[str] = []
    seen_lower: set[str] = set()
    title = (item.get("title") or "").strip()
    text = (item.get("text") or "").strip()
    combined = f"{title}\n\n{text}"
    metadata = item.get("metadata") or {}
    comments = metadata.get("comments") or []
    for c in comments:
        if isinstance(c, dict) and c.get("text"):
            combined += "\n\n" + (c.get("text") or "")[:2000]
    if title and _contains_pain(title):
        s = _first_n_words(title)
        if s and s.lower() not in seen_lower:
            snippets.append(s)
            seen_lower.add(s.lower())
    for sent in _extract_sentences(combined):
        if _contains_pain(sent) and len(snippets) < max_snippets:
            s = _first_n_words(sent)
            if s and len(s.split()) >= 3 and s.lower() not in seen_lower:
                snippets.append(s)
                seen_lower.add(s.lower())
    if not snippets and (title or text):
        # Fallback: first 12 words of title or first sentence
        fallback = _first_n_words(title or text)
        if fallback:
            snippets.append(fallback)
    return snippets[:max_snippets]
