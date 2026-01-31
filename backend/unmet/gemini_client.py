"""Gemini API: generate_content (via google-generativeai) and embeddings (via REST)."""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai
import httpx

from .config import (
    EXCLUDED_TOPICS,
    GEMINI_API_KEY,
    GEMINI_TEXT_MODEL,
    INCLUDED_TOPICS,
    NEWSLETTER_AUDIENCE,
)

logger = logging.getLogger(__name__)

EMBED_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
EMBED_BATCH_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
BATCH_SIZE = 50  # avoid rate limits


def _configure() -> None:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)


def generate_text(prompt: str, model: str | None = None, max_retries: int = 3) -> str:
    """Generate text with retries and basic rate-limit backoff."""
    _configure()
    model_name = model or GEMINI_TEXT_MODEL
    model_obj = genai.GenerativeModel(model_name)
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            r = model_obj.generate_content(prompt)
            if r.text:
                return r.text.strip()
            return ""
        except Exception as e:
            last_err = e
            if "429" in str(e) or "resource_exhausted" in str(e).lower():
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    raise last_err or RuntimeError("generate_text failed")


def classify_pain_label(text: str, title: str = "") -> tuple[str, float]:
    """
    Classify item as PAIN, DISCUSSION, NEWS, OTHER with confidence.
    Returns (label, confidence).
    """
    combined = f"Title: {title}\n\nBody: {text[:8000]}"
    prompt = f"""Classify this post/article into exactly one label: PAIN, DISCUSSION, NEWS, or OTHER.
- PAIN: complaints, requests for help, "I wish", "why can't", workflows people hate, unmet needs, frustration.
- DISCUSSION: question/discussion that could reveal pain or needs but is more exploratory.
- NEWS: factual news, product launch, announcement (not a complaint).
- OTHER: off-topic or none of the above.

Reply with exactly two lines:
Line 1: one word from PAIN|DISCUSSION|NEWS|OTHER
Line 2: confidence from 0.0 to 1.0

Content:
{combined[:6000]}
"""
    try:
        out = generate_text(prompt)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        label = "OTHER"
        conf = 0.5
        for l in lines:
            u = l.upper()
            if u in ("PAIN", "DISCUSSION", "NEWS", "OTHER"):
                label = u
                break
        for l in lines:
            try:
                v = float(l.strip())
                if 0 <= v <= 1:
                    conf = v
                    break
            except ValueError:
                continue
        return (label, conf)
    except Exception as e:
        logger.warning("classify_pain_label failed: %s", e)
        return ("OTHER", 0.0)


def classify_and_score_item(text: str, title: str = "") -> dict[str, Any]:
    """
    Classify and score one raw item. Returns dict with label, confidence, audience_fit,
    pain_intensity, actionability, evidence_spans, exclude_reason.
    If JSON parsing fails, falls back to classify_pain_label and sets scores to defaults.
    """
    included = ", ".join(INCLUDED_TOPICS[:8])
    excluded = ", ".join(EXCLUDED_TOPICS[:6])
    combined = f"Title: {title}\n\nBody: {text[:8000]}"
    prompt = f"""Audience: {NEWSLETTER_AUDIENCE}. Included topics: {included}. Excluded: {excluded} (unless directly impacts tech compliance/operations).

Classify this post/article. Output valid JSON only, no markdown, with these exact keys:
- label: one of "PAIN" | "DISCUSSION" | "NEWS" | "OTHER"
- confidence: 0.0–1.0 (be conservative; lower if unsure)
- audience_fit: 0.0–1.0 (how well it fits B2B builders/devtools founders)
- pain_intensity: 0.0–1.0
- actionability: 0.0–1.0 (how actionable the pain/opportunity is)
- evidence_spans: array of 0–5 short strings, each ≤12 words, copied VERBATIM from the content (quotes or phrases that support the label)
- topic_tags: array of 2–5 short topic tags (single words or short phrases) that describe the main themes
- claim_anchors: array of 1–3 verbatim phrases from the content, each ≤12 words, that SUPPORT the topic_tags (each tag must have at least one anchor)
- exclude_reason: string or null (if off-scope or excluded, brief reason; otherwise null)

Rules:
- If audience_fit < 0.4 then label must be NEWS or OTHER unless the content is directly about software/dev work.
- evidence_spans must be copied verbatim from the content; do not paraphrase.
- ONLY add a topic_tag if at least one claim_anchor supports it. claim_anchors must be verbatim from the content, ≤12 words each.
- Be conservative: lower confidence if unsure.

Content:
{combined[:6000]}
"""
    try:
        out = generate_text(prompt)
        raw = out.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        label = str(d.get("label", "OTHER")).upper()
        if label not in ("PAIN", "DISCUSSION", "NEWS", "OTHER"):
            label = "OTHER"
        confidence = float(d.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        audience_fit = d.get("audience_fit")
        audience_fit = max(0.0, min(1.0, float(audience_fit))) if audience_fit is not None else 0.5
        pain_intensity = d.get("pain_intensity")
        pain_intensity = max(0.0, min(1.0, float(pain_intensity))) if pain_intensity is not None else 0.5
        actionability = d.get("actionability")
        actionability = max(0.0, min(1.0, float(actionability))) if actionability is not None else 0.5
        evidence_spans = d.get("evidence_spans")
        if not isinstance(evidence_spans, list):
            evidence_spans = []
        evidence_spans = [str(s).strip()[:200] for s in evidence_spans if s][:5]
        topic_tags = d.get("topic_tags")
        if not isinstance(topic_tags, list):
            topic_tags = []
        topic_tags = [str(t).strip() for t in topic_tags if t][:5]
        claim_anchors = d.get("claim_anchors")
        if not isinstance(claim_anchors, list):
            claim_anchors = []
        claim_anchors = [str(c).strip()[:200] for c in claim_anchors if c][:3]
        claim_anchors = [" ".join(c.split()[:12]).strip() for c in claim_anchors]
        exclude_reason = d.get("exclude_reason")
        exclude_reason = str(exclude_reason).strip() or None if exclude_reason else None
        return {
            "label": label,
            "confidence": confidence,
            "audience_fit": audience_fit,
            "pain_intensity": pain_intensity,
            "actionability": actionability,
            "evidence_spans": evidence_spans,
            "topic_tags": topic_tags[:5],
            "claim_anchors": claim_anchors[:3],
            "exclude_reason": exclude_reason,
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("classify_and_score_item parse failed, using fallback: %s", e)
        label, conf = classify_pain_label(text, title)
        return {
            "label": label,
            "confidence": conf,
            "audience_fit": 0.0,
            "pain_intensity": 0.0,
            "actionability": 0.0,
            "evidence_spans": [],
            "topic_tags": [],
            "claim_anchors": [],
            "exclude_reason": "parse_fallback",
        }


def editor_gate_selection(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """
    One Gemini call per day: from top N candidates, select featured_pain_ids, secondary_pain_ids,
    catalyst_ids, and rejects. Input: list of {id, title, url, label, confidence, audience_fit,
    pain_intensity, actionability, evidence_spans}. Output: featured_pain_ids, secondary_pain_ids,
    catalyst_ids, rejects (list of {id, reason}).
    """
    if not candidates:
        return {"featured_pain_ids": [], "secondary_pain_ids": [], "catalyst_ids": [], "rejects": []}
    included = ", ".join(INCLUDED_TOPICS[:8])
    excluded = ", ".join(EXCLUDED_TOPICS[:6])
    lines = []
    for c in candidates[:50]:
        sid = c.get("id") or c.get("raw_item_id")
        lines.append(
            f"id={sid} title={c.get('title','')[:80]} url={c.get('url','')} label={c.get('label')} "
            f"audience_fit={c.get('audience_fit')} pain_intensity={c.get('pain_intensity')} actionability={c.get('actionability')} "
            f"evidence={c.get('evidence_spans', [])[:2]}"
        )
    text = "\n".join(lines)
    prompt = f"""Audience: {NEWSLETTER_AUDIENCE}. Included: {included}. Excluded: {excluded}.

You are the editor. Select which items to feature in the newsletter. Output valid JSON only, no markdown:
{{
  "featured_pain_ids": ["uuid-or-id", ...],
  "secondary_pain_ids": ["uuid-or-id", ...],
  "catalyst_ids": ["uuid-or-id", ...],
  "rejects": [{{"id": "uuid-or-id", "reason": "off-scope|weak evidence|not actionable|duplicate"}}, ...]
}}

Rules:
- Prefer high audience_fit + high pain_intensity for featured_pain_ids.
- Apply negative weight when selecting: avoid items whose evidence_spans or title suggest vague conclusions (e.g. "unclear from evidence", "not enough evidence")—prefer items with concrete evidence.
- Do NOT select off-scope items (excluded topics).
- Do NOT select duplicates (same URL or same topic).
- If insufficient good items, select fewer; empty lists are OK.
- Use the exact "id" values from the candidate list.

Candidates:
{text[:12000]}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        featured = [str(x) for x in (d.get("featured_pain_ids") or [])]
        secondary = [str(x) for x in (d.get("secondary_pain_ids") or [])]
        catalyst = [str(x) for x in (d.get("catalyst_ids") or [])]
        rejects = d.get("rejects") or []
        if not isinstance(rejects, list):
            rejects = []
        return {
            "featured_pain_ids": featured,
            "secondary_pain_ids": secondary,
            "catalyst_ids": catalyst,
            "rejects": rejects,
        }
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("editor_gate_selection parse failed: %s", e)
        # Fallback: treat all PAIN/DISCUSSION as featured, rest rejected
        id_to_label = {str(c.get("id") or c.get("raw_item_id")): c.get("label") for c in candidates}
        featured = [sid for sid, lb in id_to_label.items() if lb in ("PAIN", "DISCUSSION")][:20]
        return {
            "featured_pain_ids": featured,
            "secondary_pain_ids": [],
            "catalyst_ids": [],
            "rejects": [{"id": sid, "reason": "parse_fallback"} for sid in id_to_label if sid not in featured],
        }


def embed_batch(texts: list[str], api_key: str | None = None) -> list[list[float]]:
    """Call Gemini embed REST API in batches. Returns list of embedding vectors."""
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY required for embeddings")
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        body = {
            "requests": [
                {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": t[:8000]}]}}
                for t in chunk
            ]
        }
        url = f"{EMBED_BASE.replace('embedContent', 'batchEmbedContents')}"
        # Batch endpoint is different; use single-embed in a loop to avoid doc drift
        embeddings_chunk: list[list[float]] = []
        for t in chunk:
            single = {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t[:8000]}]},
            }
            with httpx.Client(timeout=30) as client:
                r = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={key}",
                    json=single,
                )
                r.raise_for_status()
                data = r.json()
                emb = data.get("embedding", {}).get("values", [])
                embeddings_chunk.append(emb)
            time.sleep(0.05)
        out.extend(embeddings_chunk)
    return out


def embed_single(text: str) -> list[float]:
    """Single-text embedding via REST."""
    return embed_batch([text], GEMINI_API_KEY)[0]


def embed_batch_with_retry(
    texts: list[str],
    api_key: str | None = None,
    use_subprocess: bool = True,
    batch_sizes: list[int] | None = None,
) -> list[list[float]] | None:
    """
    Run embed_batch with retry on smaller batch sizes. If use_subprocess=True (default),
    runs in subprocess so segfault/crash does not kill the main run.
    On failure after all retries, returns None (caller should use TF-IDF fallback).
    """
    if not texts:
        return []
    batch_sizes = batch_sizes or [50, 16, 4]
    last_err: Exception | None = None
    for batch_size in batch_sizes:
        try:
            if use_subprocess and len(texts) > 1:
                out: list[list[float]] = []
                for i in range(0, len(texts), batch_size):
                    chunk = texts[i : i + batch_size]
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fin:
                        json.dump(chunk, fin)
                        input_path = fin.name
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fout:
                        output_path = fout.name
                    try:
                        proc = subprocess.run(
                            [str(Path(sys.executable).resolve()), "-m", "unmet.embed_worker", input_path, output_path],
                            capture_output=True,
                            timeout=60 * (len(chunk) // 10 + 1),
                            cwd=str(Path(__file__).resolve().parent.parent),
                        )
                        if proc.returncode != 0:
                            logger.warning("embed_worker exit %s: %s", proc.returncode, proc.stderr.decode() if proc.stderr else "")
                            raise RuntimeError(f"embed_worker exited {proc.returncode}")
                        with open(output_path, encoding="utf-8") as f:
                            embs = json.load(f)
                        out.extend(embs)
                    finally:
                        Path(input_path).unlink(missing_ok=True)
                        Path(output_path).unlink(missing_ok=True)
                return out
            return embed_batch(texts, api_key)
        except Exception as e:
            last_err = e
            logger.warning("embed_batch_with_retry batch_size=%s failed: %s", batch_size, e)
            continue
    logger.error("embed_batch_with_retry failed after all batch sizes: %s", last_err)
    return None


def rename_to_match_evidence(title: str, evidence_snippets: list[str]) -> str:
    """
    If cluster title drifted from evidence, propose a new title that matches the snippets.
    Returns JSON with key new_title (string).
    """
    if not evidence_snippets:
        return title
    snippets_text = "\n".join(f"- {s}" for s in (evidence_snippets or [])[:10])
    prompt = f"""The cluster was titled "{title}" but the evidence snippets do not clearly support that topic.
Propose a short, concrete title (one phrase, ≤12 words) that matches what the snippets actually say.
Output valid JSON only, no markdown: {{ "new_title": "Your proposed title here" }}
Use only themes directly supported by the snippets. Do not invent new topics.

Snippets:
{snippets_text[:4000]}
"""
    try:
        out = generate_text(prompt)
        raw = out.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        new = (d.get("new_title") or title or "").strip()[:200]
        return new if new else title
    except Exception as e:
        logger.warning("rename_to_match_evidence failed: %s", e)
        return title


def rename_to_failure_mode(title: str, evidence_snippets: list[str]) -> str:
    """
    Rewrite cluster/card title to failure-mode phrasing (who/what fails, not domain label).
    Examples: "Software Supply Chain Vulnerabilities" → "One compromised maintainer infects downstream projects"
    """
    if not evidence_snippets:
        return title
    snippets_text = "\n".join(f"- {s}" for s in (evidence_snippets or [])[:10])
    prompt = f"""Rewrite this title into "failure-mode phrasing": a short phrase (6–10 words) that describes a CONCRETE FAILURE or RECURRING COST, not a domain label.

Bad (domain label): "Software Supply Chain Vulnerabilities", "Cloud Infrastructure Disruption", "AI Eroding Trust in Information"
Good (failure mode): "One compromised maintainer infects downstream projects", "Platform policy shifts can break CSPs overnight", "Verification pipelines can't keep up with AI output"

Current title: "{title}"

Evidence snippets (use to ground the failure):
{snippets_text[:4000]}

Output valid JSON only, no markdown: {{ "new_title": "Failure-mode title here (6–10 words)" }}
"""
    try:
        out = generate_text(prompt)
        raw = out.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        new = (d.get("new_title") or title or "").strip()[:200]
        return new if new else title
    except Exception as e:
        logger.warning("rename_to_failure_mode failed: %s", e)
        return title


def startup_grade_editor_gate(
    pain_clusters: list[dict[str, Any]],
    catalysts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    One Gemini call per day: from candidate pain clusters + catalysts, select items that can produce
    startup-grade cards (buildable wedge, identifiable buyer, workflow pain). Reject off-scope, not buildable,
    weak evidence, duplicate, news-only.
    Returns: { "selected_pain_indices": [0,1,...], "selected_catalyst_indices": [0,1,...], "rejects": [{ "kind": "pain"|"catalyst", "index": int, "reason": str }] }
    """
    if not pain_clusters and not catalysts:
        return {"selected_pain_indices": [], "selected_catalyst_indices": [], "rejects": []}

    lines: list[str] = []
    for i, c in enumerate(pain_clusters[:20]):
        title = c.get("title") or ""
        summary = (c.get("summary") or "")[:200]
        snippets = (c.get("evidence_snippets") or [])[:5]
        tags = (c.get("topic_tags") or [])[:5]
        lines.append(f"[PAIN {i}] title={title} summary={summary} topic_tags={tags} snippets={snippets[:3]}")
    for i, cat in enumerate(catalysts[:15]):
        title = cat.get("title") or ""
        what = (cat.get("what_changed") or "")[:150]
        tags = (cat.get("topic_tags") or [])[:5]
        wedge = (cat.get("opportunity_wedge") or "")[:150]
        lines.append(f"[CATALYST {i}] title={title} what_changed={what} topic_tags={tags} wedge={wedge}")

    text = "\n".join(lines)
    prompt = f"""You are the Startup-Grade Editor. Select ONLY items that can produce a buildable startup/personal-project idea card.

BUILDABILITY GATE – an item is ALLOWED only if ALL of:
- Identifiable buyer who has budget or strong motivation (not generic "developers")
- A workflow step that is blocked or costly (problem must include the workflow)
- An MVP feature that can be built/tested quickly (concrete: scanner, diff, dashboard, CLI, not "improve support")
- Falsifiable kill_criteria (how we'd learn we're wrong fast)

REJECT with reason:
- off-scope: excluded topic or not B2B/devtools
- not_buildable: cannot name buyer + workflow + concrete MVP
- weak_evidence: insufficient verbatim snippets or no clear pain
- duplicate: same theme as another selected item
- news_only: factual news only, no extractable pain/workflow/buyer (e.g. orbital data center plans with no buildable wedge)

Output valid JSON only, no markdown:
{{
  "selected_pain_indices": [0, 1],
  "selected_catalyst_indices": [0],
  "rejects": [
    {{ "kind": "pain", "index": 2, "reason": "news_only" }},
    {{ "kind": "catalyst", "index": 1, "reason": "not_buildable" }}
  ]
}}

Select 3–7 pain items and 0–5 catalyst items total so we can publish 3–5 idea cards. Prefer quality over quantity. Empty selection is OK if nothing passes.

Candidates:
{text[:14000]}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        pain_idx = d.get("selected_pain_indices") or []
        cat_idx = d.get("selected_catalyst_indices") or []
        rejects = d.get("rejects") or []
        if not isinstance(pain_idx, list):
            pain_idx = []
        if not isinstance(cat_idx, list):
            cat_idx = []
        pain_idx = [int(x) for x in pain_idx if isinstance(x, (int, float)) and 0 <= int(x) < len(pain_clusters)]
        cat_idx = [int(x) for x in cat_idx if isinstance(x, (int, float)) and 0 <= int(x) < len(catalysts)]
        return {
            "selected_pain_indices": pain_idx,
            "selected_catalyst_indices": cat_idx,
            "rejects": rejects,
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("startup_grade_editor_gate parse failed: %s", e)
        # Fallback: take first 5 pain, first 3 catalysts
        return {
            "selected_pain_indices": list(range(min(5, len(pain_clusters)))),
            "selected_catalyst_indices": list(range(min(3, len(catalysts)))),
            "rejects": [],
        }


def summarize_cluster(
    title: str,
    summary: str,
    persona: str,
    why_matters: str,
    example_links: list[str],
    item_snippets: list[str],
) -> dict[str, Any]:
    """
    Produce cluster write-up. Schema: title, moment_of_pain, summary (2 sentences),
    persona (narrow), stakes (bullets), what_people_do_now, example_urls.
    Must reference at least 2 distinct snippets; if insufficient evidence return "Insufficient evidence" title.
    """
    snippets = "\n".join(item_snippets[:15])[:12000]
    prompt = f"""You may make bounded inferences that logically follow from the evidence, as long as they are marked with tentative language ('suggests', 'likely means', 'points to', 'one plausible read') and grounded in the provided snippets. Do NOT invent new facts. Only use 'Insufficient evidence' if no reasonable inference about buyer or problem shape can be made.

You are writing a newsletter section for "pain signals" – real complaints and unmet needs from the web.
Every claim must be grounded in the snippets below. Do not invent details.

Bad: "Unclear from evidence."
Good: "Snippets show X, which suggests Y is becoming a recurring bottleneck."

Output valid JSON only, no markdown, with these exact keys:
- title: short, concrete theme (e.g. "Devs frustrated with X"). If you cannot ground the theme in at least 2 distinct snippets, use title "Insufficient evidence".
- moment_of_pain: 1 sentence scenario (what happens / what hurts).
- summary: exactly 2 sentences capturing the main pain.
- persona: narrow persona (e.g. "Backend engineers on legacy monoliths", "SaaS founders with PLG motion").
- stakes: array of 2–4 short bullet strings (workaround cost, time sink, compliance, money loss).
- what_people_do_now: 1 sentence (current workaround or coping).
- example_urls: array of URLs that appear in the snippets (use only URLs from snippets), max 5.

Rules: Reference at least 2 distinct snippets from the content. No invented details. If insufficient evidence, set title to "Insufficient evidence" and use minimal other fields.

Snippets:
{snippets}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        urls = d.get("example_urls") or []
        if not urls and example_links:
            urls = example_links[:5]
        out_title = (d.get("title") or title or "Pain signal")[:200]
        if "insufficient evidence" in out_title.lower():
            return {
                "title": out_title,
                "moment_of_pain": "",
                "summary": "",
                "persona": "",
                "stakes": [],
                "what_people_do_now": "",
                "example_urls": urls[:5],
                "why_matters": "",
            }
        return {
            "title": out_title,
            "moment_of_pain": (d.get("moment_of_pain") or "")[:500],
            "summary": (d.get("summary") or summary or "")[:1500],
            "persona": (d.get("persona") or persona or "")[:300],
            "stakes": [str(s) for s in (d.get("stakes") or [])][:5],
            "what_people_do_now": (d.get("what_people_do_now") or "")[:300],
            "example_urls": urls[:5],
            "why_matters": " ".join(d.get("stakes") or [])[:500] or (why_matters or ""),
        }
    except Exception as e:
        logger.warning("summarize_cluster failed: %s", e)
        return {
            "title": title or "Pain signal",
            "moment_of_pain": "",
            "summary": summary or "",
            "persona": persona or "",
            "stakes": [],
            "what_people_do_now": "",
            "example_urls": example_links[:5],
            "why_matters": why_matters or "",
        }


def catalyst_bullets(news_items: list[dict[str, Any]], max_bullets: int = 7) -> list[dict[str, Any]]:
    """
    Strict catalyst gating: only items that fit B2B/devtools and have narrow buyer + specific problem.
    Schema: title, what_changed, who_feels_it, problems_created (array), opportunity_wedge, confidence, source_urls, connects_to (optional).
    Exclude local human-interest (e.g. food giveaways) unless directly impacts B2B software/compliance/ops.
    Allow 0 catalysts if none pass.
    """
    if not news_items:
        return []
    excluded = ", ".join(EXCLUDED_TOPICS[:6])
    text = "\n\n".join(
        [
            f"Title: {x.get('title','')}\nURL: {x.get('url','')}\nSnippet: {(x.get('text') or x.get('title') or '')[:500]}"
            for x in news_items[:30]
        ]
    )
    prompt = f"""You may make bounded inferences that logically follow from the evidence, as long as they are marked with tentative language ('suggests', 'likely means', 'points to', 'one plausible read') and grounded in the provided snippets. Do NOT invent new facts. If exact product is unclear, propose the narrowest plausible starting wedge using tentative language. Only use 'Unclear from evidence' if even a buyer cannot be inferred.

Audience: {NEWSLETTER_AUDIENCE}. Excluded (do NOT include unless directly impacts tech compliance/ops): {excluded}.

From these news items, output catalysts that create urgency or new problems for B2B builders. Output valid JSON array only, no markdown.
Each object must have: title, topic_tags (array of 2–5 short tags for distinctness), what_changed (1 factual sentence), who_feels_it (narrow persona), problems_created (array of 2+ concrete headaches), opportunity_wedge ("Start with <buyer> who <situation>, build <first feature>." — use tentative language if needed; only "Unclear from evidence." if even a buyer cannot be inferred), confidence (0.0–1.0), source_urls (array of URLs from items), connects_to (optional: 1 sentence linking this catalyst to a theme if relevant). Avoid overlapping topic_tags with other catalysts unless connects_to adds a new sub-angle.

Hard rules:
- Do NOT include local human-interest (e.g. food giveaways, sports, celebrity) unless it directly impacts B2B software/compliance/operations.
- If you cannot name a narrow buyer and specific problem, do NOT include the item.
- OK to return 0 catalysts (empty array) if none pass.
- Wedge: If exact product is unclear, propose the narrowest plausible starting wedge with tentative language. Only output "Unclear from evidence" if even a buyer cannot be inferred.

News items:
{text[:15000]}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        arr = json.loads(raw) if raw.startswith("[") else []
        if not isinstance(arr, list):
            arr = []
        out = []
        for x in arr[:max_bullets]:
            wedge = str(x.get("opportunity_wedge") or "Unclear from evidence.").strip()
            if not wedge.endswith("."):
                wedge = wedge + "."
            problems = x.get("problems_created")
            if isinstance(problems, list):
                problems_list = [str(p) for p in problems][:5]
            else:
                problems_list = [str(problems)] if problems else []
            out.append({
                "title": str(x.get("title", ""))[:200],
                "topic_tags": [str(t) for t in (x.get("topic_tags") or [])][:5],
                "what_changed": str(x.get("what_changed") or "")[:500],
                "who_feels_it": str(x.get("who_feels_it") or "")[:200],
                "problems_created": problems_list,
                "opportunity_wedge": wedge[:300],
                "confidence": max(0.0, min(1.0, float(x.get("confidence", 0.5)))),
                "source_urls": [str(u) for u in (x.get("source_urls") or [])][:3],
                "summary": str(x.get("what_changed") or x.get("summary") or "")[:800],
                "interests": [],
                "connects_to": str(x.get("connects_to") or "").strip()[:300] or None,
            })
        return out
    except Exception as e:
        logger.warning("catalyst_bullets failed: %s", e)
        return []


def compose_idea_cards(
    pain_clusters: list[dict[str, Any]],
    catalysts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    One Gemini call: merge selected pain clusters + catalysts into 3–5 idea cards (themes).
    Output: array of cards with idea_title, hook, what_happened, pain_signal {claim, evidence_snippets, links},
    catalyst_signal {claim, evidence_snippets, links}, why_now [], wedge (exact format or "Unclear from evidence."),
    confidence, inference (1 sentence combining pain + catalyst).
    Hard: every claim supported by evidence snippets; no duplicate URLs across cards.
    """
    if not pain_clusters and not catalysts:
        return []
    pain_text = "\n\n".join(
        [
            f"[Pain] title={c.get('title','')} summary={c.get('summary','')[:300]} snippets={c.get('evidence_snippets', [])[:5]} links={c.get('example_urls', c.get('links', []))[:3]}"
            for c in pain_clusters[:15]
        ]
    )
    cat_text = "\n\n".join(
        [
            f"[Catalyst] title={c.get('title','')} what_changed={c.get('what_changed','')[:200]} source_urls={c.get('source_urls', [])[:3]}"
            for c in catalysts[:15]
        ]
    )
    prompt = f"""You may make bounded inferences that logically follow from the evidence, as long as they are marked with tentative language ('suggests', 'likely means', 'points to', 'one plausible read') and grounded in the provided snippets. Do NOT invent new facts. Only use 'Unclear from evidence' if no reasonable inference about buyer or problem shape can be made.

Bad: "Unclear from evidence."
Good: "Snippets show X, which suggests Y is becoming a recurring bottleneck."

Merge the following pain clusters and catalysts into 3–5 idea cards (themes). Output valid JSON array only, no markdown.
Each card must have:
- idea_title: short theme title
- hook: 1 sentence hook (8–14 words)
- what_happened: 1–2 sentences
- pain_signal: {{ "claim": "...", "evidence_snippets": ["...", "..."], "links": ["url", ...] }}
- catalyst_signal: {{ "claim": "...", "evidence_snippets": ["...", "..."], "links": ["url", ...] }} (can be empty claim if no catalyst)
- why_now: array of 1–3 short strings
- wedge: exactly "Start with <buyer> who <situation>, build <first feature>." or "Unclear from evidence." (use tentative language for plausible wedge; only Unclear if buyer cannot be inferred)
- confidence: 0.0–1.0
- inference: 1 sentence combining pain + catalyst into what this suggests (use tentative language)

Hard constraints: Every claim must be supported by the evidence_snippets you list. No duplicate URLs across cards (each URL at most once in the whole output). Use only URLs from the input.

Pain clusters:
{pain_text[:8000]}

Catalysts:
{cat_text[:6000]}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        arr = json.loads(raw) if raw.startswith("[") else []
        if not isinstance(arr, list):
            arr = []
        seen_urls: set[str] = set()
        out = []
        for card in arr[:5]:
            if not isinstance(card, dict):
                continue
            ps = card.get("pain_signal") or {}
            cs = card.get("catalyst_signal") or {}
            links = list(ps.get("links") or []) + list(cs.get("links") or [])
            dup = [u for u in links if u and u in seen_urls]
            if dup:
                continue  # skip card with duplicate URL
            for u in links:
                if u:
                    seen_urls.add(u)
            wedge = str(card.get("wedge") or "Unclear from evidence.").strip()
            if not wedge.endswith("."):
                wedge = wedge + "."
            out.append({
                "idea_title": str(card.get("idea_title") or "")[:200],
                "hook": str(card.get("hook") or "")[:500],
                "what_happened": str(card.get("what_happened") or "")[:800],
                "pain_signal": {
                    "claim": str(ps.get("claim") or "")[:500],
                    "evidence_snippets": [str(s) for s in (ps.get("evidence_snippets") or [])][:5],
                    "links": [str(u) for u in (ps.get("links") or [])][:3],
                },
                "catalyst_signal": {
                    "claim": str(cs.get("claim") or "")[:500],
                    "evidence_snippets": [str(s) for s in (cs.get("evidence_snippets") or [])][:5],
                    "links": [str(u) for u in (cs.get("links") or [])][:3],
                },
                "why_now": [str(w) for w in (card.get("why_now") or [])][:3],
                "wedge": wedge[:300],
                "confidence": max(0.0, min(1.0, float(card.get("confidence", 0.5)))),
                "inference": str(card.get("inference") or "")[:400],
            })
        return out
    except Exception as e:
        logger.warning("compose_idea_cards failed: %s", e)
        return []


# Minimum fraction of evidence bullets that must include a comment permalink (sanity check)
EVIDENCE_COMMENT_PERMALINK_MIN_RATIO = 0.70


def _format_evidence_bullets_for_prompt(bullets: list[dict[str, Any]]) -> str:
    """Format evidence_bullets for the LLM: quote — Post: url — Comment: url or (none)."""
    lines = []
    for b in (bullets or [])[:15]:
        quote = (b.get("quote") or "").strip()[:200]
        post_url = b.get("post_url") or ""
        comment_url = b.get("comment_url") or "(none)"
        lines.append(f'- "{quote}" — Post: {post_url} — Comment: {comment_url}')
    return "\n".join(lines) if lines else "(no structured evidence)"


def _normalize_evidence_item(e: Any) -> dict[str, Any]:
    """Normalize evidence entry to { quote, post_url, comment_url }. Legacy: string -> post_url/comment_url null."""
    if isinstance(e, dict):
        return {
            "quote": str(e.get("quote") or "").strip()[:200],
            "post_url": (e.get("post_url") or "").strip() or None,
            "comment_url": (e.get("comment_url") or "").strip() or None,
        }
    return {"quote": str(e).strip()[:200], "post_url": None, "comment_url": None}


def _evidence_comment_permalink_ratio(evidence: list[Any]) -> float:
    """Fraction of evidence bullets that have a comment permalink (comment_url)."""
    if not evidence:
        return 0.0
    normalized = [_normalize_evidence_item(e) for e in evidence]
    with_comment = sum(1 for n in normalized if n.get("comment_url"))
    return with_comment / len(normalized)


def compose_startup_grade_cards(
    pain_clusters: list[dict[str, Any]],
    catalysts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    One Gemini call: merge selected pain clusters + catalysts into 3–5 Startup-Grade Idea Cards.
    Problem-centric, comment-derived evidence with post + comment permalinks. If <70% of evidence
    bullets have comment permalinks, confidence is auto-downgraded.
    """
    if not pain_clusters and not catalysts:
        return []

    pain_parts = []
    for c in pain_clusters[:15]:
        bullets = c.get("evidence_bullets") or []
        bullets_text = _format_evidence_bullets_for_prompt(bullets)
        pain_parts.append(
            f"[Pain] title={c.get('title','')} summary={c.get('summary','')[:300]}\nEvidence (quote — Post — Comment):\n{bullets_text}"
        )
    pain_text = "\n\n".join(pain_parts)
    cat_text = "\n\n".join(
        [
            f"[Catalyst] title={c.get('title','')} what_changed={c.get('what_changed','')[:200]} topic_tags={c.get('topic_tags', [])[:5]} source_urls={c.get('source_urls', [])[:3]}"
            for c in catalysts[:15]
        ]
    )

    prompt = f"""You are an analyst writing for Unmet. You are given a set of Hacker News posts and deep comment threads (many comments per post). Your job is NOT to summarize. Your job is to extract startup-grade, buildable problems with paying buyers.

HARD RULES:
1) Comments are the primary signal. Use posts only for context.
2) Evidence must be forensic, not abstract.
   - Prefer direct quotes from comments.
   - If paraphrasing, it must clearly imply a quotable comment.
3) Every evidence bullet MUST include:
   - a short quote/paraphrase
   - the HN post link (https://news.ycombinator.com/item?id=POST_ID)
   - the specific HN comment link when available (https://news.ycombinator.com/item?id=COMMENT_ID)
4) A single problem may be supported by multiple HN posts. Prefer problems with multi-thread support.
5) Only include problems that block someone from doing their job or create measurable risk (time, money, reliability, security).
6) Explicitly state who pays (role + why it hits their metrics/budget).
7) Add "Why existing tools fail" (1 sentence).
8) "Why now" must include a forcing function (deadline, outage, policy change, platform shift, cost inflection).
9) The wedge must be narrow, avoid automating core decisions, and be shippable by a small team in <90 days.
10) If evidence is weak (post-only, no comment permalinks, vague claims), say so and lower confidence.

OUTPUT FORMAT (STRICT). Output valid JSON array only, no markdown. 3–5 cards. Each card:
{{
  "title": "Problem Title (failure-mode phrasing)",
  "hook": "8–14 words",
  "problem": "One sentence.",
  "evidence": [
    {{ "quote": "short quote or paraphrase", "post_url": "https://news.ycombinator.com/item?id=POST_ID", "comment_url": "https://news.ycombinator.com/item?id=COMMENT_ID or null" }},
    ...
  ],
  "who_pays": "Role + metric/budget impact.",
  "why_existing_tools_fail": "One sentence.",
  "why_now": ["Forcing function.", ...],
  "wedge": {{
    "icp": "Start with <buyer> who <situation>",
    "mvp": "<first feature>",
    "why_they_pay": "<metric>",
    "first_channel": "<channel>",
    "anti_feature": "<what you won't build>"
  }},
  "confidence": "high|med|low (based on independent commenters + cross-post support + evidence quality)",
  "kill_criteria": "Clear invalidation condition."
}}

Pain clusters (use only the Evidence links provided; do not invent URLs):
{pain_text[:12000]}

Catalysts:
{cat_text[:6000]}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        arr = json.loads(raw) if raw.startswith("[") else []
        if not isinstance(arr, list):
            arr = []
        out: list[dict[str, Any]] = []
        for card in arr[:5]:
            if not isinstance(card, dict):
                continue
            wedge = card.get("wedge")
            if isinstance(wedge, dict):
                wedge_out = {
                    "icp": str(wedge.get("icp") or "").strip()[:300],
                    "mvp": str(wedge.get("mvp") or "").strip()[:300],
                    "why_they_pay": str(wedge.get("why_they_pay") or "").strip()[:200],
                    "first_channel": str(wedge.get("first_channel") or "").strip()[:200],
                    "anti_feature": str(wedge.get("anti_feature") or "").strip()[:200],
                }
            else:
                wedge_out = {"icp": "", "mvp": "", "why_they_pay": "", "first_channel": "", "anti_feature": ""}
            evidence_raw = card.get("evidence") or []
            evidence_normalized = [_normalize_evidence_item(e) for e in evidence_raw][:5]
            conf = (card.get("confidence") or "med").strip().lower()
            if conf not in ("low", "med", "high"):
                conf = "med"
            ratio = _evidence_comment_permalink_ratio(evidence_normalized)
            if ratio < EVIDENCE_COMMENT_PERMALINK_MIN_RATIO and conf == "high":
                conf = "med"
                logger.info("evidence_comment_permalink_ratio=%.2f < %.2f; downgraded confidence to med", ratio, EVIDENCE_COMMENT_PERMALINK_MIN_RATIO)
            elif ratio < EVIDENCE_COMMENT_PERMALINK_MIN_RATIO and conf == "med":
                conf = "low"
                logger.info("evidence_comment_permalink_ratio=%.2f < %.2f; downgraded confidence to low", ratio, EVIDENCE_COMMENT_PERMALINK_MIN_RATIO)
            out.append({
                "title": str(card.get("title") or "")[:200],
                "hook": str(card.get("hook") or "")[:500],
                "problem": str(card.get("problem") or "")[:500],
                "evidence": evidence_normalized,
                "who_pays": str(card.get("who_pays") or "")[:200],
                "why_existing_tools_fail": str(card.get("why_existing_tools_fail") or "").strip()[:300],
                "stakes": [str(s).strip()[:200] for s in (card.get("stakes") or [])][:5],
                "why_now": [str(w).strip()[:300] for w in (card.get("why_now") or [])][:5],
                "wedge": wedge_out,
                "confidence": conf,
                "kill_criteria": str(card.get("kill_criteria") or "").strip()[:300],
            })
        return out
    except Exception as e:
        logger.warning("compose_startup_grade_cards failed: %s", e)
        return []


def generate_one_bet(cards: list[dict[str, Any]]) -> str:
    """
    One macro prediction from the set of published cards (not a wedge).
    E.g. "Teams will treat AI output as hostile input by default."
    """
    if not cards:
        return "Worth exploring: re-run with more data."
    titles = [c.get("title") or "" for c in cards[:5]]
    problems = [c.get("problem") or "" for c in cards[:5]]
    text = "\n".join([f"Card: {t}\nProblem: {p}" for t, p in zip(titles, problems)])
    prompt = f"""From these startup-grade idea cards, state ONE macro prediction (a trend or shift), not a product wedge.
Example: "Teams will treat AI output as hostile input by default." or "Compliance will become a first-class build step."
Output a single sentence only, no preamble.

Cards:
{text[:3000]}
"""
    try:
        out = generate_text(prompt)
        line = (out or "").strip().split("\n")[0].strip()
        return line[:300] if line else "Worth exploring: re-run with more data."
    except Exception as e:
        logger.warning("generate_one_bet failed: %s", e)
        return "Worth exploring: re-run with more data."
