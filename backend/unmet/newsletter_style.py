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

# Startup-grade card: additional banned noise (tag lines, filler, unclear spam)
STARTUP_GRADE_BANNED_PHRASES = list(BANNED_PHRASES) + [
    "unclear from evidence",
    "not enough evidence",
    "not enough info",
    "unclear from the evidence",
    "ai proliferation",
    "encryption concerns",
    "ai proliferation / encryption",
    "this highlights",
    "need for robust",
]

# MVP must include at least one tangible artifact (tooling/workflow)
MVP_TANGIBLE_WORDS = [
    "scanner", "diff", "verifier", "simulator", "dashboard", "cli", "webhook",
    "api", "tool", "plugin", "check", "report", "runner", "pipeline",
    "notifier", "bot", "script", "widget", "layer", "gate", "guard",
    "linter", "checker", "monitor", "audit", "export", "sync",
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


# ---- Startup-Grade Idea Cards (schema + validation + formatting) ----


def _startup_card_contains_banned(text: str) -> bool:
    lower = (text or "").lower()
    return any(b in lower for b in STARTUP_GRADE_BANNED_PHRASES)


def _title_implies_failure_mode(title: str) -> bool:
    """Title should contain a verb or imply failure (not just a noun phrase like 'Software Supply Chain')."""
    if not title or len(title.strip()) < 5:
        return False
    t = title.strip().lower()
    # Common failure-mode patterns: "X can Y", "X breaks", "X fails", "one X does Y", "X can't keep up", etc.
    failure_indicators = [
        " can ", " can't ", " cannot ", " breaks ", " fail", " fails ", " break ",
        " infects ", " erodes ", " can't keep ", " won't ", " doesn't ", " don't ",
        " blocks ", " block ", " breaks ", " break ", " lose ", " loses ",
        " one ", " single ", " overnight ", " can't ", " unable to ",
    ]
    if any(p in t for p in failure_indicators):
        return True
    # Verb-like: ends with -s/-ed/-ing or contains common verbs
    words = t.split()
    verbs = {"break", "fail", "infect", "block", "lose", "cost", "hurt", "break", "drop", "miss"}
    if any(w.rstrip("s") in verbs or w.rstrip("ed") in verbs or w.rstrip("ing") in verbs for w in words):
        return True
    # "X → Y" or "X vs Y" or "when X" imply a scenario
    if " when " in t or " → " in t or " vs " in t:
        return True
    # Reject pure noun phrases (e.g. "Software Supply Chain Vulnerabilities", "Cloud Infrastructure Disruption")
    if len(words) >= 5:
        return True
    return False


def _mvp_has_tangible_artifact(mvp: str) -> bool:
    """MVP must include a tangible artifact: scanner, diff, verifier, dashboard, CLI, etc."""
    if not mvp or len(mvp.strip()) < 10:
        return False
    lower = mvp.lower()
    return any(w in lower for w in MVP_TANGIBLE_WORDS)


def _who_pays_has_role_and_org(who_pays: str) -> bool:
    """who_pays must include role + org type (not generic 'developers')."""
    if not who_pays or len(who_pays.strip()) < 5:
        return False
    lower = who_pays.lower()
    if "developer" in lower and ("startup" not in lower and "team" not in lower and "company" not in lower and "org" not in lower and "enterprise" not in lower):
        if lower.strip() in ("developers", "developer"):
            return False
    # Must have at least two meaningful parts (role + context)
    words = [w for w in who_pays.split() if len(w) > 1]
    return len(words) >= 2


# Stakes: at least one in time, reliability, security, money; proxy/estimate allowed if explicit
STAKES_CATEGORY_WORDS = {
    "time": ["time", "hours", "days", "latency", "delay", "mttr", "engineer-hours", "weeks"],
    "reliability": ["reliability", "outage", "downtime", "incident", "sev", "availability", "uptime"],
    "security": ["security", "breach", "compliance", "vulnerability", "risk", "exposure"],
    "money": ["cost", "money", "budget", "spend", "waste", "pay", "dollar", "revenue"],
}
STAKES_PROXY_LABELS = ["estimate", "proxy", "likely", "roughly", "approx"]


def _stake_acceptable(stake: str) -> bool:
    """One stake item is acceptable if it touches time/reliability/security/money; proxy labels allowed."""
    if not (stake or "").strip():
        return False
    lower = (stake or "").lower()
    has_category = any(
        any(w in lower for w in words)
        for words in STAKES_CATEGORY_WORDS.values()
    )
    return has_category


def _stakes_acceptable(stakes: list[Any]) -> bool:
    """Must include at least one stake in time, reliability, security, or money; proxy/estimate allowed if explicit."""
    if not isinstance(stakes, list) or len(stakes) < 1:
        return False
    for s in stakes:
        text = (str(s) or "").strip()
        if _stake_acceptable(text):
            return True
    return False


def validate_startup_grade_card_split(
    card: dict[str, Any],
    allowed_urls: set[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """
    Validate startup-grade card; split into HARD_FAIL (drop), SOFT_FAIL (repair), and warnings.
    Returns (hard_fail, soft_fail, warnings).
    HARD_FAIL: evidence missing or no post_url; invented links; buyer undefined ("developers"); problem pure news.
    SOFT_FAIL: missing who_blocked; missing/weak stakes; evidence wrong shape; comment_url missing.
    """
    hard: list[str] = []
    soft: list[str] = []
    warnings: list[str] = []

    if not isinstance(card, dict):
        return (["card must be a dict"], [], [])
    allowed_urls = allowed_urls or set()

    title = (card.get("title") or "").strip()
    hook = (card.get("hook") or "").strip()
    problem = (card.get("problem") or "").strip()
    evidence = card.get("evidence")
    who_pays = (card.get("who_pays") or "").strip()
    stakes = card.get("stakes")
    why_now = card.get("why_now")
    wedge = card.get("wedge")
    confidence = (card.get("confidence") or "med").strip().lower()
    kill_criteria = (card.get("kill_criteria") or "").strip()

    # ---- Required fields (missing -> hard so we don't render garbage)
    if not title:
        hard.append("title required")
    elif len(title.split()) < 4 or len(title.split()) > 12:
        soft.append("title must be 4–12 words")
    elif not _title_implies_failure_mode(title):
        hard.append("title must imply failure mode")

    if not hook:
        hard.append("hook required")
    elif len(hook.split()) < 8 or len(hook.split()) > 14:
        soft.append("hook must be 8–14 words")

    if not problem:
        hard.append("problem required")
    else:
        pl = problem.lower()
        has_who = any(p in pl for p in (" who ", " whom ", " teams ", " they ", " engineers ", " developers ", " founders ", " ops ", " platform ", " sec ", " sre ", " appsec "))
        if not has_who:
            soft.append("problem should include who is blocked (who/teams/role)")

    # ---- Evidence: missing or no post_url -> HARD; invented links -> HARD; wrong shape / no comment_url -> SOFT/warning
    if evidence is None or not isinstance(evidence, list):
        hard.append("evidence missing entirely")
    elif len(evidence) < 1:
        hard.append("evidence missing entirely")
    else:
        has_post_url = False
        evidence_wrong_shape = False
        for e in evidence[:10]:
            if isinstance(e, dict):
                quote = (e.get("quote") or "").strip()
                post_url = (e.get("post_url") or "").strip()
                comment_url = (e.get("comment_url") or "").strip()
                if post_url and (not allowed_urls or post_url in allowed_urls):
                    has_post_url = True
                if allowed_urls and post_url and post_url not in allowed_urls:
                    hard.append("evidence contains invented post link")
                if allowed_urls and comment_url and comment_url not in allowed_urls:
                    hard.append("evidence contains invented comment link")
                if not quote:
                    soft.append("evidence bullet missing quote")
                elif len(quote.split()) > 12:
                    soft.append("evidence quote must be ≤12 words")
                if not comment_url:
                    warnings.append("comment link missing")
            else:
                evidence_wrong_shape = True
                s = (str(e) or "").strip()
                if s and len(s.split()) <= 12:
                    has_post_url = True  # legacy string evidence; we'll repair to object with post_url from context
        if not has_post_url and len(evidence) >= 1:
            hard.append("evidence has no post_url links")
        if evidence_wrong_shape:
            soft.append("evidence items should be objects with quote, post_url, comment_url")

    # ---- Who pays: undefined "developers" only -> HARD; missing or weak -> SOFT
    if not who_pays:
        soft.append("who_pays missing")
    elif who_pays.lower().strip() in ("developers", "developer"):
        hard.append("buyer/owner undefined (generic 'developers' with no role/team)")
    elif not _who_pays_has_role_and_org(who_pays):
        soft.append("who_pays should include role + org type")

    # ---- Stakes: must have at least one in time/reliability/security/money; proxy allowed
    if not _stakes_acceptable(stakes):
        soft.append("stakes must include at least one (time, reliability, security, money); proxy/estimate allowed if labeled")

    # ---- Wedge
    if not isinstance(wedge, dict):
        hard.append("wedge must be object")
    else:
        mvp = (wedge.get("mvp") or "").strip()
        if not mvp:
            hard.append("wedge.mvp required")
        elif not _mvp_has_tangible_artifact(mvp):
            soft.append("wedge.mvp should include tangible artifact (scanner, diff, CLI, etc.)")
        for k in ("icp", "why_they_pay", "first_channel", "anti_feature"):
            if not (wedge.get(k) or "").strip():
                soft.append(f"wedge.{k} missing")

    if not kill_criteria:
        hard.append("kill_criteria required")

    if confidence and confidence not in ("low", "med", "high"):
        soft.append("confidence must be low|med|high")

    for block in [title, hook, problem, who_pays, kill_criteria]:
        if _startup_card_contains_banned(block):
            hard.append("banned phrase in content")
            break
    if isinstance(wedge, dict):
        for k in ("icp", "mvp", "why_they_pay", "first_channel", "anti_feature"):
            if _startup_card_contains_banned(str(wedge.get(k) or "")):
                hard.append("banned phrase in wedge")
                break
    if isinstance(why_now, list):
        for w in why_now:
            if _startup_card_contains_banned(str(w)):
                hard.append("banned phrase in why_now")
                break

    return (hard, soft, warnings)


def repair_startup_grade_card(
    card: dict[str, Any],
    cluster_links: list[str] | None = None,
) -> dict[str, Any]:
    """
    Auto-repair SOFT_FAIL issues: infer who_blocked, add proxy stakes, normalize evidence to objects.
    Never invents URLs; uses cluster_links only for post_url when normalizing string evidence.
    """
    card = dict(card)
    cluster_links = list(cluster_links or [])[:5]
    default_post_url = cluster_links[0] if cluster_links else None

    # Infer who_pays from title/problem if missing or generic
    who_pays = (card.get("who_pays") or "").strip()
    if not who_pays or not _who_pays_has_role_and_org(who_pays):
        title = (card.get("title") or "").lower()
        problem = (card.get("problem") or "").lower()
        if "security" in title or "security" in problem or "vulnerability" in title or "vuln" in problem:
            who_pays = "SecEng / AppSec teams at product companies"
        elif "api" in title or "api" in problem or "call" in title:
            who_pays = "Platform / backend teams at scale"
        elif "offline" in title or "private" in title or "scan" in title:
            who_pays = "Security and compliance teams in regulated orgs"
        elif "ai" in title or "code" in title or "generated" in title:
            who_pays = "Engineering leads and platform teams shipping AI-generated code"
        else:
            who_pays = who_pays or "Platform / SRE teams at product companies"
        card["who_pays"] = who_pays

    # Normalize evidence to list of {quote, post_url, comment_url}
    evidence = card.get("evidence")
    if isinstance(evidence, list) and evidence:
        normalized = []
        for e in evidence[:10]:
            if isinstance(e, dict):
                normalized.append({
                    "quote": (e.get("quote") or "").strip()[:200],
                    "post_url": (e.get("post_url") or "").strip() or None,
                    "comment_url": (e.get("comment_url") or "").strip() or None,
                })
            else:
                normalized.append({
                    "quote": (str(e) or "").strip()[:200],
                    "post_url": default_post_url,
                    "comment_url": None,
                })
        card["evidence"] = normalized

    # Add proxy stakes if missing or empty
    stakes = card.get("stakes")
    if not _stakes_acceptable(stakes):
        proxy = [
            "Estimate: engineer-hours and MTTR risk when incidents recur.",
            "Proxy: reliability and security impact (likely sev escalation if unaddressed).",
        ]
        existing = list(stakes)[:3] if isinstance(stakes, list) else []
        card["stakes"] = proxy + existing

    # Downgrade confidence if we repaired
    conf = (card.get("confidence") or "med").strip().lower()
    if conf not in ("low", "med", "high"):
        conf = "med"
    if conf == "high":
        conf = "med"
    card["confidence"] = conf

    return card


def validate_startup_grade_card(card: dict[str, Any], allowed_urls: set[str] | None = None) -> list[str]:
    """
    Validate startup-grade card schema and buildability rules.
    Returns list of error messages (hard + soft); empty if valid.
    Use validate_startup_grade_card_split for HARD vs SOFT separation.
    """
    hard, soft, _ = validate_startup_grade_card_split(card, allowed_urls=allowed_urls)
    return hard + soft


def _evidence_bullet_to_str(e: Any) -> str:
    """Format one evidence bullet: quote — Post: url — Comment: url or (none)."""
    if isinstance(e, dict):
        quote = (e.get("quote") or "").strip()
        post_url = (e.get("post_url") or "").strip() or "(none)"
        comment_url = (e.get("comment_url") or "").strip() or "(none)"
        return f'"{quote}" — Post: {post_url} — Comment: {comment_url}'
    return str(e).strip()


def format_startup_grade_card(
    card: dict[str, Any],
    warnings: list[str] | None = None,
    is_draft: bool = False,
) -> str:
    """Render one startup-grade idea card as markdown. Evidence with post + comment links. Optionally show warnings and draft label."""
    warnings = list(warnings or [])
    lines = []
    if is_draft:
        lines.append("*(Draft — needs more receipts)*")
        lines.append("")
    lines.append(f"### **{card.get('title') or 'Idea'}**")
    lines.append("")
    lines.append(card.get("hook") or "")
    lines.append("")
    lines.append(f"**Problem:** {card.get('problem') or ''}")
    lines.append("")
    evidence = card.get("evidence") or []
    if evidence:
        lines.append("**Evidence:**")
        for e in evidence[:5]:
            lines.append(f"- {_evidence_bullet_to_str(e)}")
        lines.append("")
    lines.append(f"**Who pays:** {card.get('who_pays') or ''}")
    why_fail = (card.get("why_existing_tools_fail") or "").strip()
    if why_fail:
        lines.append(f"**Why existing tools fail:** {why_fail}")
    stakes = card.get("stakes") or []
    if stakes:
        lines.append("**Stakes:**")
        for s in stakes[:3]:
            if s:
                lines.append(f"- {s}")
        lines.append("")
    why_now = card.get("why_now") or []
    if why_now:
        lines.append("**Why now:**")
        for w in why_now[:3]:
            if w:
                lines.append(f"- {w}")
        lines.append("")
    wedge = card.get("wedge") or {}
    if wedge:
        lines.append("**Wedge:**")
        lines.append(f"- ICP: {wedge.get('icp') or ''}")
        lines.append(f"- MVP: {wedge.get('mvp') or ''}")
        lines.append(f"- Why they pay: {wedge.get('why_they_pay') or ''}")
        lines.append(f"- First channel: {wedge.get('first_channel') or ''}")
        lines.append(f"- Anti-feature: {wedge.get('anti_feature') or ''}")
        lines.append("")
    conf = (card.get("confidence") or "med").lower()
    if conf in ("low", "med", "high"):
        lines.append(f"**Confidence:** {conf}")
    lines.append("")
    kc = card.get("kill_criteria") or ""
    if kc:
        lines.append(f"**Kill criteria:** {kc}")
    if warnings:
        lines.append("")
        lines.append("**Warnings:** " + "; ".join(warnings))
    lines.append("")
    return "\n".join(lines)


def get_todays_themes_from_startup_cards(cards: list[dict[str, Any]], top_n: int = 3) -> str:
    """Return 'Today's themes: X, Y, Z.' from startup-grade card titles (top 2–3)."""
    titles = [c.get("title") or "" for c in (cards or [])[:top_n] if c.get("title")]
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
