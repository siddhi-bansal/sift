"""Gemini API: generate_content (via google-generativeai) and embeddings (via REST)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import google.generativeai as genai
import httpx

from .config import GEMINI_API_KEY, GEMINI_TEXT_MODEL

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


def summarize_cluster(
    title: str,
    summary: str,
    persona: str,
    why_matters: str,
    example_links: list[str],
    item_snippets: list[str],
) -> dict[str, str]:
    """Produce title, 2–3 sentence summary, persona, why_matters, 3–5 example links."""
    snippets = "\n".join(item_snippets[:15][:12000])
    prompt = f"""You are writing a newsletter section for "pain signals" – real complaints and unmet needs from the web.

Based on these post snippets, produce a short cluster write-up in JSON with keys: title, summary, persona, why_matters, example_urls.
- title: short, concrete theme (e.g. "Devs frustrated with X").
- summary: 2–3 sentences capturing the main pain.
- persona: who is affected (e.g. "Backend engineers", "SaaS founders").
- why_matters: workaround cost, time sink, compliance, money loss, or other stakes.
- example_urls: array of 3–5 URLs from the snippets to use as links (use only URLs that appear in the snippets).

Snippets:
{snippets}

Reply with only valid JSON, no markdown."""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        urls = d.get("example_urls") or []
        if not urls and example_links:
            urls = example_links[:5]
        return {
            "title": (d.get("title") or title or "Pain signal")[:200],
            "summary": (d.get("summary") or summary or "")[:1500],
            "persona": (d.get("persona") or persona or "")[:300],
            "why_matters": (d.get("why_matters") or why_matters or "")[:500],
            "example_urls": urls[:5],
        }
    except Exception as e:
        logger.warning("summarize_cluster failed: %s", e)
        return {
            "title": title or "Pain signal",
            "summary": summary or "",
            "persona": persona or "",
            "why_matters": why_matters or "",
            "example_urls": example_links[:5],
        }


def catalyst_bullets(news_items: list[dict[str, Any]], max_bullets: int = 7) -> list[dict[str, Any]]:
    """
    From news items (RSS), produce 3–7 catalyst bullets.
    Each: title, summary (1–2 sentences), interests, problems_created, source_urls.
    """
    if not news_items:
        return []
    text = "\n\n".join(
        [
            f"Title: {x.get('title','')}\nURL: {x.get('url','')}\nSnippet: {(x.get('text') or x.get('title') or '')[:500]}"
            for x in news_items[:30]
        ]
    )
    prompt = f"""From these news items, identify 3–7 "catalyst" bullets: industry-wide events that create urgency or new problems.
For each bullet output a JSON object with: title, summary (1–2 sentences), interests (list of topic names like "AI/ML", "SaaS"), problems_created (what new problems or urgency this creates), source_urls (list of 1–2 URLs from the items).

Reply with a JSON array of such objects. Only valid JSON.
News items:
{text[:15000]}
"""
    try:
        raw = generate_text(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        arr = json.loads(raw) if raw.startswith("[") else []
        return [
            {
                "title": str(x.get("title", ""))[:200],
                "summary": str(x.get("summary", ""))[:800],
                "interests": [str(i) for i in (x.get("interests") or [])][:5],
                "problems_created": str(x.get("problems_created") or "")[:500],
                "source_urls": [str(u) for u in (x.get("source_urls") or [])][:3],
            }
            for x in (arr if isinstance(arr, list) else [])[:max_bullets]
        ]
    except Exception as e:
        logger.warning("catalyst_bullets failed: %s", e)
        return []
