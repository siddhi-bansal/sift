"""Reddit via Apify (no Reddit API approval). Default actor: trudax/reddit-scraper. Set APIFY_REDDIT_ACTOR to override."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..config import APIFY_API_TOKEN, APIFY_REDDIT_ACTOR, REDDIT_POSTS_PER_SUB

logger = logging.getLogger(__name__)


def _parse_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(float(v), tz=timezone.utc)
        except (OSError, ValueError):
            return None
    if isinstance(v, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(v.replace("Z", "+00:00"), fmt)
            except ValueError:
                continue
    return None


def _item_to_raw(item: dict[str, Any], subreddit: str) -> dict[str, Any]:
    """Map Apify dataset item to raw_items row. Tolerate varying field names."""
    url = item.get("url") or item.get("link") or item.get("permalink")
    if url and not url.startswith("http"):
        url = f"https://reddit.com{url}" if url.startswith("/") else f"https://reddit.com/{url}"
    title = (item.get("title") or item.get("headline") or "")[:500]
    body = item.get("body") or item.get("text") or item.get("selftext") or item.get("content") or ""
    text = f"{title}\n\n{body}" if body else title
    author = item.get("author") or item.get("username")
    created = _parse_ts(item.get("createdAt") or item.get("created_utc") or item.get("timestamp"))
    sid = item.get("id") or item.get("postId") or str(abs(hash((url or "", title, subreddit))))
    score = item.get("score") or item.get("upvotes") or 0
    return {
        "source": "reddit",
        "source_id": f"{subreddit}_{sid}".strip("_"),
        "url": (url or "")[:2000],
        "title": title[:500],
        "text": (text or "")[:50000],
        "author": str(author) if author else None,
        "published_at": created,
        "metadata": {"subreddit": subreddit, "score": score, "via": "apify"},
    }


def fetch_reddit_via_apify(
    subreddits: list[str],
    posts_per_sub: int | None = None,
    actor_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch Reddit posts via Apify (no Reddit API key). Uses vulnv/reddit-posts-scraper by default.
    Set APIFY_API_TOKEN in env. Returns list of dicts for raw_items.
    """
    posts_per_sub = posts_per_sub if posts_per_sub is not None else REDDIT_POSTS_PER_SUB
    if not subreddits:
        return []
    if not APIFY_API_TOKEN:
        logger.warning("APIFY_API_TOKEN not set; skipping Apify Reddit")
        return []
    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.warning("apify-client not installed; pip install apify-client")
        return []

    actor = actor_id or APIFY_REDDIT_ACTOR or "trudax/reddit-scraper"
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        client = ApifyClient(APIFY_API_TOKEN)
        for sub in subreddits:
            try:
                run_input = {
                    "startUrls": [{"url": f"https://www.reddit.com/r/{sub.strip()}/"}],
                    "maxItems": min(posts_per_sub * 2, 500),
                    "maxPostCount": posts_per_sub,
                    "maxComments": 0,
                    "proxy": {"useApifyProxy": True},
                }
                run = client.actor(actor).call(run_input=run_input)
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    # Only treat post-like items (often type post or has title+url)
                    if item.get("type") == "comment" and not item.get("title"):
                        continue
                    sub_name = item.get("subreddit") or sub
                    row = _item_to_raw(item, sub_name)
                    key = row["source_id"]
                    if key not in seen:
                        seen.add(key)
                        out.append(row)
            except Exception as e:
                logger.warning("Apify Reddit subreddit %s failed: %s", sub, e)
    except Exception as e:
        logger.warning("Apify Reddit ingest failed: %s", e)
    return out
