"""Heuristic pain-score from complaint/ask language patterns."""
from __future__ import annotations

import re
from typing import Any


# Phrases that suggest pain / unmet need
PAIN_PHRASES = [
    r"\bi wish\b", r"\bwhy can'?t\b", r"\bhow do i\b", r"\bdoes anyone else\b",
    r"\bhate (that|when|how)\b", r"\bfrustrat(e|ed|ing)\b", r"\bannoy(e|ing|ed)\b",
    r"\bstruggl(e|ing)\b", r"\bproblem with\b", r"\bissue with\b", r"\bbug(gy)?\b",
    r"\bbroken\b", r"\bsucks\b", r"\bterrible\b", r"\bworst\b", r"\bunusable\b",
    r"\bplease (add|fix|support)\b", r"\bis there (a|an) (easy|simple) way\b",
    r"\brecommend(ations?)?\b", r"\balternative to\b", r"\blooking for\b",
    r"\bneed (a|to)\b", r"\bwant (to|a)\b", r"\bwould (love|like) (to|a)\b",
    r"\bhoping (for|to)\b", r"\brequest\b", r"\bfeature request\b",
]
COMPILED = [re.compile(p, re.I) for p in PAIN_PHRASES]


def pain_score_heuristic(text: str, title: str = "") -> float:
    """
    Return a heuristic score 0..1 from complaint/ask patterns.
    Combines title and text.
    """
    combined = f"{title}\n{text}" if title else text
    if not combined.strip():
        return 0.0
    combined = combined.lower()
    hits = sum(1 for p in COMPILED if p.search(combined))
    # Normalize to roughly 0..1 (cap at 1)
    return min(1.0, hits * 0.15 + (0.2 if "?" in combined else 0))
