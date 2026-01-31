"""Hacker News via official Firebase REST API."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import HN_POST_LIMIT, HN_COMMENTS_PER_POST

logger = logging.getLogger(__name__)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"

# Keywords that boost comment relevance (pain/workflow signals). Used for ranking, not hard filter.
COMMENT_PAIN_KEYWORDS = [
    "we had to", "this broke", "in production", "on-call", "incident", "workaround",
    "we ended up", "security", "migration", "blocked", "failed", "can't", "cannot",
    "hate", "frustrat", "broken", "stuck", "problem", "issue", "bug", "wish", "need",
]


def _fetch_json(url: str, client: httpx.Client) -> Any:
    r = client.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def _comment_pain_score(text: str) -> int:
    """Score comment by pain/workflow keyword matches (boost, not filter)."""
    if not text:
        return 0
    lower = text.lower()
    return sum(1 for kw in COMMENT_PAIN_KEYWORDS if kw in lower)


def fetch_hn_stories(
    post_limit: int | None = None,
    comments_per_post: int | None = None,
    include_comments: bool | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch HN stories with deep comments. Fewer posts (default 25), more comments per post (default 30).
    Prefers posts with higher comment activity (descendants). Comments are stored with post_id, comment_id,
    author, created_at, text, and derived permalinks (post_url, comment_url).
    Returns list of dicts ready for raw_items: source, source_id, url, title, text, author, published_at, metadata.
    """
    post_limit = post_limit if post_limit is not None else HN_POST_LIMIT
    comments_per_post = comments_per_post if comments_per_post is not None else HN_COMMENTS_PER_POST
    include_comments = include_comments if include_comments is not None else (comments_per_post > 0)

    # 1) Fetch story IDs from top + new, then fetch each story to get descendants for ranking
    candidate_stories: list[dict[str, Any]] = []
    seen: set[str] = set()
    with httpx.Client(timeout=20) as client:
        for endpoint in ("topstories", "newstories"):
            try:
                ids = _fetch_json(f"{HN_BASE}/{endpoint}.json", client)
                if not isinstance(ids, list):
                    continue
                # Fetch more candidates so we can rank by descendants
                for item_id in ids[: max(post_limit * 2, 60)]:
                    if str(item_id) in seen:
                        continue
                    seen.add(str(item_id))
                    try:
                        item = _fetch_json(f"{HN_BASE}/item/{item_id}.json", client)
                    except Exception as e:
                        logger.debug("HN item %s failed: %s", item_id, e)
                        continue
                    if not item or item.get("type") != "story":
                        continue
                    candidate_stories.append(item)
            except Exception as e:
                logger.warning("HN %s failed: %s", endpoint, e)

    # 2) Rank by comment activity (descendants), take top post_limit
    candidate_stories.sort(key=lambda x: (x.get("descendants") or 0, x.get("score") or 0), reverse=True)
    stories = candidate_stories[:post_limit]

    # 3) Build output with comments (post_id, comment_id, author, created_at, text, post_url, comment_url)
    out: list[dict[str, Any]] = []
    with httpx.Client(timeout=20) as client:
        for item in stories:
            item_id = item.get("id")
            if item_id is None:
                continue
            url = item.get("url") or HN_ITEM_URL.format(id=item_id)
            title = (item.get("title") or "")[:500]
            text = item.get("title", "")
            if item.get("text"):
                text = f"{text}\n\n{item.get('text','')}"
            text = (text or "")[:50000]
            published = None
            if item.get("time"):
                try:
                    published = datetime.fromtimestamp(int(item["time"]), tz=timezone.utc)
                except Exception:
                    pass
            metadata: dict[str, Any] = {
                "score": item.get("score"),
                "descendants": item.get("descendants"),
            }
            if include_comments and item.get("kids"):
                metadata["comments"] = _fetch_comments_with_permalinks(
                    client,
                    post_id=item_id,
                    kid_ids=item["kids"],
                    limit=comments_per_post,
                )
            out.append({
                "source": "hn",
                "source_id": str(item_id),
                "url": url,
                "title": title,
                "text": text,
                "author": item.get("by"),
                "published_at": published,
                "metadata": metadata,
            })
    return out


def _fetch_comments_with_permalinks(
    client: httpx.Client,
    post_id: int,
    kid_ids: list[int],
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    Fetch up to limit comments. Store post_id, comment_id, author, created_at, text.
    Derive post_url and comment_url. Use keyword boost to prioritize pain/workflow comments;
    do not filter so aggressively that we end up with <20 comments (fetch and score, take top limit).
    """
    post_url = HN_ITEM_URL.format(id=post_id)
    # Fetch more candidates so we can rank by pain score and still have enough comments
    fetch_count = min(max(limit + 20, 50), len(kid_ids))
    candidates: list[dict[str, Any]] = []
    for cid in kid_ids[:fetch_count]:
        try:
            comment = _fetch_json(f"{HN_BASE}/item/{cid}.json", client)
            if not comment or comment.get("type") != "comment":
                continue
            text = (comment.get("text") or "").strip()
            if not text:
                continue
            created_at = None
            if comment.get("time"):
                try:
                    created_at = datetime.fromtimestamp(int(comment["time"]), tz=timezone.utc).isoformat()
                except Exception:
                    pass
            candidates.append({
                "post_id": str(post_id),
                "comment_id": str(cid),
                "author": comment.get("by"),
                "created_at": created_at,
                "text": text[:2000],
                "post_url": post_url,
                "comment_url": HN_ITEM_URL.format(id=cid),
                "_pain_score": _comment_pain_score(text),
            })
        except Exception as e:
            logger.debug("HN comment %s failed: %s", cid, e)
    # Sort by pain score desc so pain-signal comments come first; take top limit (ensure at least min if we have them)
    candidates.sort(key=lambda c: (c.pop("_pain_score", 0), len(c.get("text", ""))), reverse=True)
    return candidates[:limit]
