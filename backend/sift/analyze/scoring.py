"""Deterministic filtering and ranking: Sift score, noise_penalty, candidate filter, top N."""
from __future__ import annotations

import logging
from typing import Any

from ..config import EDITOR_GATE_TOP_N

logger = logging.getLogger(__name__)

# Weights for sift_score
AUDIENCE_FIT_WEIGHT = 0.35
PAIN_INTENSITY_WEIGHT = 0.30
ACTIONABILITY_WEIGHT = 0.25
CONFIDENCE_WEIGHT = 0.10

# Candidate filter thresholds
MIN_AUDIENCE_FIT = 0.65
MIN_PAIN_OR_ACTIONABILITY = 0.50  # pain_intensity >= 0.50 OR actionability >= 0.60
MIN_ACTIONABILITY_ALT = 0.60
MIN_CONFIDENCE = 0.55

# Noise penalties (deterministic)
PENALTY_SHOW_HN_NON_PAIN = 0.25
PENALTY_RSS_NO_PAIN_EVIDENCE = 0.25
PENALTY_EXCLUDE_REASON = 0.20


def noise_penalty(item: dict[str, Any], label: str, source: str, evidence_spans: list[str]) -> float:
    """
    Deterministic noise penalty. Returns value to subtract from score.
    - +0.25 if title contains "Show HN" and label != PAIN
    - +0.25 if source is generic RSS and no evidence spans indicate pain
    - +0.20 if exclude_reason is set
    """
    penalty = 0.0
    title = (item.get("title") or "").lower()
    if "show hn" in title and label != "PAIN":
        penalty += PENALTY_SHOW_HN_NON_PAIN
    if source and source.lower() == "rss" and not evidence_spans:
        # Generic RSS with no evidence spans that indicate pain
        penalty += PENALTY_RSS_NO_PAIN_EVIDENCE
    if item.get("exclude_reason"):
        penalty += PENALTY_EXCLUDE_REASON
    return penalty


def _evidence_indicates_pain(evidence_spans: list[str]) -> bool:
    """Heuristic: any span contains pain-like words."""
    pain_words = {"blocked", "locked", "can't", "failed", "billing", "support", "hate", "frustrat", "broken", "sucks", "worst", "wish", "need"}
    text = " ".join(evidence_spans).lower()
    return any(w in text for w in pain_words)


def sift_score(
    audience_fit: float,
    pain_intensity: float,
    actionability: float,
    confidence: float,
    noise_penalty_val: float,
) -> float:
    """
    sift_score = 0.35*audience_fit + 0.30*pain_intensity + 0.25*actionability + 0.10*confidence - noise_penalty
    """
    raw = (
        AUDIENCE_FIT_WEIGHT * max(0, min(1, audience_fit))
        + PAIN_INTENSITY_WEIGHT * max(0, min(1, pain_intensity))
        + ACTIONABILITY_WEIGHT * max(0, min(1, actionability))
        + CONFIDENCE_WEIGHT * max(0, min(1, confidence))
    )
    return max(0.0, raw - noise_penalty_val)


def passes_candidate_filter(
    label: str,
    audience_fit: float | None,
    pain_intensity: float | None,
    actionability: float | None,
    confidence: float | None,
) -> bool:
    """
    Keep items where:
    - label in {PAIN, DISCUSSION}
    - audience_fit >= 0.65 (or relaxed when new columns missing)
    - (pain_intensity >= 0.50 OR actionability >= 0.60)
    - confidence >= 0.55
    When audience_fit/pain_intensity/actionability are None (old schema), use label + confidence only.
    """
    if label not in ("PAIN", "DISCUSSION"):
        return False
    conf = confidence if confidence is not None else 0.0
    if conf < MIN_CONFIDENCE:
        return False
    # Backward compat: if new score columns missing, pass by label + confidence
    if audience_fit is None and pain_intensity is None and actionability is None:
        return True
    af = audience_fit if audience_fit is not None else 0.0
    if af < MIN_AUDIENCE_FIT:
        return False
    pi = pain_intensity if pain_intensity is not None else 0.0
    ac = actionability if actionability is not None else 0.0
    if pi < MIN_PAIN_OR_ACTIONABILITY and ac < MIN_ACTIONABILITY_ALT:
        return False
    return True


def filter_and_rank_candidates(
    items: list[dict[str, Any]],
    labels_map: dict[str, dict[str, Any]],
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """
    For each item, compute sift_score; keep only candidates passing filter; sort by score desc; return top N.
    Each item must have id, title, url, source. labels_map: raw_item_id -> {label, confidence, audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason}.
    """
    top_n = top_n if top_n is not None else EDITOR_GATE_TOP_N
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in items:
        rid = str(r.get("id", ""))
        lab = labels_map.get(rid, {})
        label = lab.get("label") or "OTHER"
        audience_fit = lab.get("audience_fit")
        pain_intensity = lab.get("pain_intensity")
        actionability = lab.get("actionability")
        confidence = lab.get("confidence")
        evidence_spans = lab.get("evidence_spans") or []
        exclude_reason = lab.get("exclude_reason")
        if not passes_candidate_filter(label, audience_fit, pain_intensity, actionability, confidence):
            continue
        af = float(audience_fit) if audience_fit is not None else 0.0
        pi = float(pain_intensity) if pain_intensity is not None else 0.0
        ac = float(actionability) if actionability is not None else 0.0
        conf = float(confidence) if confidence is not None else 0.0
        item_with_reason = dict(r)
        item_with_reason["exclude_reason"] = exclude_reason
        np_val = noise_penalty(item_with_reason, label, r.get("source") or "", evidence_spans)
        score = sift_score(af, pi, ac, conf, np_val)
        scored.append((score, {**r, "sift_score": score, "label": label, **lab}))
    scored.sort(key=lambda x: -x[0])
    return [x[1] for x in scored[:top_n]]
