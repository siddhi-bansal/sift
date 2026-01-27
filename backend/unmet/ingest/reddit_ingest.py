"""Reddit via PRAW."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, REDDIT_POSTS_PER_SUB

logger = logging.getLogger(__name__)


def fetch_reddit_posts(
    subreddits: list[str],
    posts_per_sub: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch top/hot/new from each subreddit. Returns list of dicts for raw_items.
    """
    posts_per_sub = posts_per_sub if posts_per_sub is not None else REDDIT_POSTS_PER_SUB
    if not subreddits:
        return []
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.warning("Reddit credentials missing; skipping Reddit ingest")
        return []
    try:
        import praw
    except ImportError:
        logger.warning("praw not installed; skipping Reddit ingest")
        return []

    out: list[dict[str, Any]] = []
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT or "UnmetNewsletter/1.0",
        )
        for sub_name in subreddits:
            try:
                sub = reddit.subreddit(sub_name)
                for kind in ("hot", "top", "new"):
                    try:
                        gen = getattr(sub, kind)(limit=posts_per_sub // 3 + 1)
                        for p in gen:
                            try:
                                created = datetime.fromtimestamp(p.created_utc, tz=timezone.utc)
                            except Exception:
                                created = None
                            text = (p.title or "") + "\n\n" + (getattr(p, "selftext", None) or "")
                            out.append({
                                "source": "reddit",
                                "source_id": f"{sub_name}_{p.id}",
                                "url": f"https://reddit.com{p.permalink}" if getattr(p, "permalink", None) else None,
                                "title": (p.title or "")[:500],
                                "text": (text or "")[:50000],
                                "author": str(p.author) if p.author else None,
                                "published_at": created,
                                "metadata": {"subreddit": sub_name, "score": getattr(p, "score", 0)},
                            })
                    except Exception as e:
                        logger.debug("Reddit %s %s failed: %s", sub_name, kind, e)
            except Exception as e:
                logger.warning("Reddit subreddit %s failed: %s", sub_name, e)
    except Exception as e:
        logger.warning("Reddit ingest failed: %s", e)
    return out
