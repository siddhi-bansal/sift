"""Newsletter formatting and rewriting: schema, validation, banned phrases, evidence grounding.

Output is skimmable, plain English, builder lens, and non-hallucinatory:
every claim must be traceable to evidence snippets + links.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def _generate_text(prompt: str) -> str:
    """Lazy import to avoid loading Gemini when use_gemini=False (e.g. render_sample)."""
    from .gemini_client import generate_text
    return generate_text(prompt)

# Banned vague/corporate phrases — generator must avoid these
BANNED_PHRASES = [
    "this highlights",
    "this showcases",
    "this contributes",
    "raises questions about",
    "existing tools are often",
    "need for robust",
    "increased competition",
]


@dataclass
class EvidenceBundle:
    """Raw evidence from source: snippets (≤12 words each) and links (max 3)."""
    snippets: list[str]  # verbatim or titles; each ≤12 words
    links: list[str]  # max 3


@dataclass
class NewsletterItem:
    """Strict schema for one newsletter item (pain cluster, rising, catalyst, wildcard)."""
    hook: str
    explanation: str
    why_bullets: list[str]
    who: str
    wedge: str
    evidence_snippets: list[str]
    links: list[str]
    strength_or_impact: str  # "Low" | "Med" | "High"

    def word_count_excluding_links(self) -> int:
        total = (
            len(self.hook.split())
            + len(self.explanation.split())
            + sum(len(b.split()) for b in self.why_bullets)
            + len(self.who.split())
            + len(self.wedge.split())
            + sum(len(s.split()) for s in self.evidence_snippets)
        )
        return total

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook": self.hook,
            "explanation": self.explanation,
            "why_bullets": self.why_bullets,
            "who": self.who,
            "wedge": self.wedge,
            "evidence_snippets": self.evidence_snippets,
            "links": self.links[:3],
            "strength_or_impact": self.strength_or_impact,
        }


def _snippet_ok(s: str, max_words: int = 12) -> bool:
    return len(s.split()) <= max_words and len(s.strip()) > 0


def _contains_banned_phrase(text: str) -> bool:
    lower = text.lower()
    return any(b in lower for b in BANNED_PHRASES)


def validate_item(item: NewsletterItem) -> list[str]:
    """Return list of validation errors; empty if valid."""
    errs: list[str] = []
    wc = item.word_count_excluding_links()
    if wc > 120:
        errs.append(f"word_count_excluding_links={wc} > 120")
    if len(item.links) > 3:
        errs.append(f"links count {len(item.links)} > 3")
    if not item.evidence_snippets:
        errs.append("evidence_snippets required")
    if not item.links:
        errs.append("at least one link required")
    for s in item.evidence_snippets:
        if not _snippet_ok(s):
            errs.append(f"evidence snippet must be ≤12 words: {s[:50]!r}")
    if len(item.hook.split()) < 8 or len(item.hook.split()) > 14:
        errs.append("hook must be 8–14 words")
    if item.hook.lower().startswith("this article") or item.hook.lower().startswith("this post"):
        errs.append("hook must not start with 'This article' / 'This post'")
    if item.strength_or_impact not in ("Low", "Med", "High"):
        errs.append("strength_or_impact must be Low, Med, or High")
    for block in [item.explanation, item.who, item.wedge] + item.why_bullets:
        if _contains_banned_phrase(block):
            errs.append("banned phrase in content")
    return errs


def _deterministic_fallback(
    draft: dict[str, Any],
    item_type: str,
    evidence: EvidenceBundle,
    strength_or_impact: str,
) -> NewsletterItem:
    """Fallback when Gemini JSON is invalid: use existing text only, no new claims."""
    title = (draft.get("title") or "Item")[:80]
    summary = (draft.get("summary") or "")[:200]
    persona = (draft.get("persona") or "")[:80]
    why = (draft.get("why_matters") or summary)[:150]
    snippets = evidence.snippets[:3]
    links = evidence.links[:3]
    # Hook from title only (8–14 words) so it stays one clean line
    words = title.split()[:14]
    hook = " ".join(words).strip()
    if len(hook.split()) < 8:
        hook = (hook + " — worth watching.").strip()
    hook = " ".join(hook.split()[:14])
    wedge_fallback = "Unclear from evidence." if not (persona and summary) else "Start with builders who face this, build the first feature that unblocks them."
    return NewsletterItem(
        hook=hook,
        explanation=summary[:300] if summary else "See evidence.",
        why_bullets=[why] if why else ["See links below."],
        who=persona or "Builders and operators",
        wedge=wedge_fallback,
        evidence_snippets=snippets,
        links=links,
        strength_or_impact=strength_or_impact if strength_or_impact in ("Low", "Med", "High") else "Med",
    )


def rewrite_into_template(
    draft: dict[str, Any],
    item_type: str,
    evidence: EvidenceBundle,
    strength_or_impact: str,
    *,
    use_gemini: bool = True,
) -> NewsletterItem:
    """
    Produce a strict NewsletterItem from draft + evidence.
    use_gemini=False skips LLM and uses deterministic fallback (for tests/sample).
    """
    strength_or_impact = strength_or_impact if strength_or_impact in ("Low", "Med", "High") else "Med"
    snippets_text = "\n".join(f"- {s}" for s in evidence.snippets[:5])
    links_text = "\n".join(evidence.links[:3])

    if not use_gemini:
        return _deterministic_fallback(draft, item_type, evidence, strength_or_impact)

    prompt = f"""You may make bounded inferences that logically follow from the evidence, as long as they are marked with tentative language ('suggests', 'likely means', 'points to', 'one plausible read') and grounded in the provided snippets. Do NOT invent new facts. Only use 'Unclear from evidence' if no reasonable inference about buyer or problem shape can be made.

Bad: "Unclear from evidence."
Good: "Snippets show X, which suggests Y is becoming a recurring bottleneck."

Rewrite this {item_type} into a strict newsletter item. EVERY claim must be supported by the evidence below. Do not invent tool names, company names, numbers, quotes, or timelines.

BANNED PHRASES (do not use): "This highlights", "This showcases", "This contributes", "raises questions about", "Existing tools are often", "need for robust", "increased competition".
Use direct language: "Teams are doing X because…", "The bottleneck is…", "This creates an opening for…"

Draft:
- title: {draft.get('title') or ''}
- summary: {draft.get('summary') or ''}
- persona: {draft.get('persona') or ''}
- why_matters: {draft.get('why_matters') or ''}

Evidence (use only these; pull verbatim snippets ≤12 words or use titles):
{snippets_text}

Links (use only these, max 3):
{links_text}

Output valid JSON only, no markdown, with these exact keys:
{{
  "hook": "Bold hook sentence, 8–14 words, no 'This article…'",
  "explanation": "1–2 sentences, simple English, evidence-grounded",
  "why_bullets": ["bullet one", "bullet two", "bullet three"],
  "who": "one short line, persona who feels this",
  "wedge": "one short line, plausible buildable wedge grounded in evidence",
  "evidence_snippets": ["snippet1 ≤12 words", "snippet2", "snippet3"],
  "links": ["url1", "url2", "url3"],
  "strength_or_impact": "{strength_or_impact}"
}}

Rules: hook 8–14 words. evidence_snippets must be from the evidence above (verbatim or titles). links must be from the links above, max 3. Total text ≤120 words excluding links.
WEDGE: If exact product is unclear, propose the narrowest plausible starting wedge using tentative language. Only output "Unclear from evidence" if even a buyer cannot be inferred. Prefer format "Start with <buyer> who <situation>, build <first feature>." with tentative wording when needed.
Require at least 1 evidence_snippet related to stakes if available. If unsure, use guarded language: "Seems like…", "One plausible read…", "Could indicate…"
"""

    for attempt in range(2):
        try:
            raw = _generate_text(prompt)
            raw = raw.strip().removeprefix("```json").removeprefix("```").strip().removesuffix("```").strip()
            obj = json.loads(raw)
            item = NewsletterItem(
                hook=str(obj.get("hook") or "").strip(),
                explanation=str(obj.get("explanation") or "").strip(),
                why_bullets=[str(x).strip() for x in (obj.get("why_bullets") or [])][:3],
                who=str(obj.get("who") or "").strip(),
                wedge=str(obj.get("wedge") or "").strip(),
                evidence_snippets=[str(x).strip() for x in (obj.get("evidence_snippets") or [])][:3],
                links=[str(x).strip() for x in (obj.get("links") or [])][:3],
                strength_or_impact=str(obj.get("strength_or_impact") or strength_or_impact).strip() or strength_or_impact,
            )
            # Normalize to Low/Med/High
            if item.strength_or_impact not in ("Low", "Med", "High"):
                item.strength_or_impact = strength_or_impact
            # Ensure links come from evidence only
            item.links = [u for u in item.links if u in evidence.links][:3] or evidence.links[:3]
            errs = validate_item(item)
            if not errs:
                return item
            if attempt == 0:
                repair_prompt = f"""The previous JSON was invalid: {errs}. Fix and output only valid JSON with the same keys (hook, explanation, why_bullets, who, wedge, evidence_snippets, links, strength_or_impact)."""
                raw = _generate_text(repair_prompt)
                raw = raw.strip().removeprefix("```json").removeprefix("```").strip().removesuffix("```").strip()
                obj = json.loads(raw)
                item = NewsletterItem(
                    hook=str(obj.get("hook") or "").strip(),
                    explanation=str(obj.get("explanation") or "").strip(),
                    why_bullets=[str(x).strip() for x in (obj.get("why_bullets") or [])][:3],
                    who=str(obj.get("who") or "").strip(),
                    wedge=str(obj.get("wedge") or "").strip(),
                    evidence_snippets=[str(x).strip() for x in (obj.get("evidence_snippets") or [])][:3],
                    links=[str(x).strip() for x in (obj.get("links") or [])][:3],
                    strength_or_impact=str(obj.get("strength_or_impact") or strength_or_impact).strip() or strength_or_impact,
                )
                if item.strength_or_impact not in ("Low", "Med", "High"):
                    item.strength_or_impact = strength_or_impact
                item.links = [u for u in item.links if u in evidence.links][:3] or evidence.links[:3]
                errs = validate_item(item)
                if not errs:
                    return item
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("rewrite_into_template parse error (attempt %s): %s", attempt + 1, e)
    return _deterministic_fallback(draft, item_type, evidence, strength_or_impact)


def format_item(item: NewsletterItem, section_kind: str) -> str:
    """Render one NewsletterItem as markdown (bold hook, bullets, who, wedge, evidence).
    section_kind: 'catalyst' uses Impact; else uses Signal strength."""
    lines = [
        f"### **{item.hook}**",
        "",
        item.explanation,
        "",
    ]
    for b in item.why_bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append(f"**Who:** {item.who}")
    lines.append(f"**Possible wedge:** {item.wedge}")
    if section_kind == "catalyst":
        lines.append(f"**Impact:** {item.strength_or_impact}")
    else:
        lines.append(f"**Signal strength:** {item.strength_or_impact}")
    lines.append("")
    lines.append("**Evidence:** " + "; ".join(item.evidence_snippets[:3]))
    for u in item.links[:3]:
        if u:
            lines.append(f"- {u}")
    lines.append("")
    return "\n".join(lines)


def get_intro() -> str:
    """Short intro (2–3 lines): what Unmet is and that claims are evidence-based."""
    return """Unmet scans HN, Reddit, and RSS for pain signals and catalyst news, then clusters and summarizes them. Every claim below is tied to evidence—snippets and links—with no invented names, numbers, or causal leaps. When we're unsure, we say so."""


def get_pattern_language(cluster_titles: list[str], catalyst_titles: list[str], max_lines: int = 2) -> str:
    """Return 1–2 lines like 'Today clusters around: X' from cluster and catalyst titles. No hallucination."""
    themes: list[str] = []
    for t in (cluster_titles or [])[:5]:
        if t and t.strip():
            themes.append(t.strip())
    for t in (catalyst_titles or [])[:3]:
        if t and t.strip() and t.strip() not in themes:
            themes.append(t.strip())
    if not themes:
        return ""
    # Dedupe while preserving order
    seen = set()
    unique = []
    for t in themes:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            unique.append(t)
    head = ", ".join(unique[:5])
    return f"Today clusters around: {head}."


def get_todays_themes_from_idea_cards(idea_cards: list[dict[str, Any]], top_n: int = 3) -> str:
    """Return 'Today's themes: X, Y, Z.' from idea_card.idea_title (top 2–3)."""
    titles = [c.get("idea_title") or "" for c in (idea_cards or [])[:top_n] if c.get("idea_title")]
    titles = [t.strip() for t in titles if t.strip()]
    if not titles:
        return ""
    return "Today's themes: " + ", ".join(titles) + "."


def format_idea_card(card: dict[str, Any]) -> str:
    """Render one idea card as markdown: idea_title, hook, what_happened, pain_signal, catalyst_signal, why_now, wedge, inference, evidence."""
    lines = [
        f"### **{card.get('idea_title') or 'Theme'}**",
        "",
        card.get("hook") or "",
        "",
        card.get("what_happened") or "",
        "",
    ]
    ps = card.get("pain_signal") or {}
    if ps.get("claim"):
        lines.append("**Pain signal:** " + (ps.get("claim") or ""))
        if ps.get("evidence_snippets"):
            lines.append("Evidence: " + "; ".join(ps.get("evidence_snippets", [])[:3]))
        if ps.get("links"):
            for u in (ps.get("links") or [])[:3]:
                if u:
                    lines.append(f"- {u}")
        lines.append("")
    cs = card.get("catalyst_signal") or {}
    if cs.get("claim"):
        lines.append("**Catalyst signal:** " + (cs.get("claim") or ""))
        if cs.get("evidence_snippets"):
            lines.append("Evidence: " + "; ".join(cs.get("evidence_snippets", [])[:3]))
        if cs.get("links"):
            for u in (cs.get("links") or [])[:3]:
                if u:
                    lines.append(f"- {u}")
        lines.append("")
    why_now = card.get("why_now") or []
    if why_now:
        for w in why_now[:3]:
            if w:
                lines.append(f"- {w}")
        lines.append("")
    wedge = card.get("wedge") or ""
    if wedge:
        lines.append(f"**Wedge:** {wedge}")
    inference = card.get("inference") or ""
    if inference:
        lines.append(f"**Inference:** {inference}")
    lines.append("")
    lines.append(f"**Confidence:** {card.get('confidence', 0):.2f}")
    lines.append("")
    return "\n".join(lines)


def build_one_line_bet(
    items: list[tuple[NewsletterItem, float]],
    threshold_low: float = 0.4,
) -> str:
    """
    One sentence at the end: the most buildable wedge of the day.
    items are (NewsletterItem, buildability_score). If all scores < threshold_low, use "Worth exploring: …".
    """
    if not items:
        return "Worth exploring: re-run with more data."
    best = max(items, key=lambda x: x[1])
    item, score = best
    prefix = "One line I'd bet on:" if score >= threshold_low else "Worth exploring:"
    return f"{prefix} {item.wedge}"


def evidence_from_cluster_items(
    items: list[dict[str, Any]],
    max_snippets: int = 3,
    max_links: int = 3,
) -> EvidenceBundle:
    """Build EvidenceBundle from cluster raw items. Prefer raw_items.evidence_snippets when present; else title/text ≤12 words."""
    snippets: list[str] = []
    links: list[str] = []
    for x in items[:15]:
        url = x.get("url")
        if url and url not in links:
            links.append(url)
        # Prefer stored evidence_snippets (from HN comments + pain language extraction)
        item_snippets = x.get("evidence_snippets")
        if isinstance(item_snippets, list) and item_snippets:
            for s in item_snippets:
                s = (s or "").strip()
                if s and len(s.split()) <= 12 and s not in snippets:
                    snippets.append(s)
                    if len(snippets) >= max_snippets:
                        break
        if len(snippets) >= max_snippets:
            break
    if len(snippets) < max_snippets:
        for x in items[:15]:
            title = (x.get("title") or "").strip()
            text = (x.get("text") or "")[:200]
            if title:
                words = title.split()[:12]
                s = " ".join(words)
                if s and s not in snippets:
                    snippets.append(s)
            if text and len(snippets) < max_snippets:
                words = text.replace("\n", " ").split()[:12]
                if words:
                    s = " ".join(words)
                    if s not in snippets:
                        snippets.append(s)
    return EvidenceBundle(
        snippets=list(dict.fromkeys(snippets))[:max_snippets],
        links=links[:max_links],
    )


def evidence_from_catalyst(cat: dict[str, Any], snippets_from_summary: bool = True) -> EvidenceBundle:
    """Build EvidenceBundle from a catalyst item (title, summary, source_urls)."""
    links = list(cat.get("source_urls") or [])[:3]
    snips: list[str] = []
    title = (cat.get("title") or "").strip()
    if title:
        snips.append(" ".join(title.split()[:12]))
    if snippets_from_summary:
        summary = (cat.get("summary") or "").strip()
        if summary:
            snips.append(" ".join(summary.split()[:12]))
    return EvidenceBundle(snippets=snips[:3], links=links[:3])


def signal_strength_from_cluster(
    size: int,
    avg_pain: float,
    avg_confidence: float,
) -> str:
    """
    Low/Med/High from cluster size, avg pain_score, and avg model confidence.
    Heuristic: High if size>=5 and (avg_pain>=0.5 or avg_conf>=0.7); Med if size>=2 or scores decent; else Low.
    """
    if size >= 5 and (avg_pain >= 0.5 or avg_confidence >= 0.7):
        return "High"
    if size >= 2 or avg_pain >= 0.4 or avg_confidence >= 0.5:
        return "Med"
    return "Low"


def impact_from_catalyst(
    interest_count: int,
    source_url_count: int,
    has_urgency: bool,
) -> str:
    """
    Low/Med/High from interest-match count, source credibility (url count), urgency keywords.
    Heuristic: High if (interests>=2 and urls>=1) or urgency; Med if interests>=1 or urls>=2; else Low.
    """
    if (interest_count >= 2 and source_url_count >= 1) or has_urgency:
        return "High"
    if interest_count >= 1 or source_url_count >= 2:
        return "Med"
    return "Low"


_URGENCY_WORDS = {"urgent", "deadline", "must", "critical", "breaking", "immediate", "compliance", "regulation", "required"}


def has_urgency_keywords(text: str) -> bool:
    return any(w in (text or "").lower() for w in _URGENCY_WORDS)


def buildability_score_pain(signal_strength: str, who: str, wedge: str) -> float:
    """Buildability for pain clusters: signal strength + persona clarity + wedge specificity."""
    base = {"Low": 0.2, "Med": 0.5, "High": 0.8}.get(signal_strength, 0.4)
    if who and len(who.split()) >= 2:
        base += 0.1
    if wedge and len(wedge.split()) >= 5:
        base += 0.1
    return min(1.0, base)


def buildability_score_catalyst(impact: str, problems_text: str) -> float:
    """Buildability for catalysts: impact + directness of new buyer pain."""
    base = {"Low": 0.2, "Med": 0.5, "High": 0.8}.get(impact, 0.4)
    if problems_text and len(problems_text.split()) >= 5:
        base += 0.15
    return min(1.0, base)
