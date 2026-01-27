"""RSS feed ingestion."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import feedparser

from ..config import RSS_ENTRIES_PER_FEED

logger = logging.getLogger(__name__)


def fetch_rss_items(
    urls: list[str],
    entries_per_feed: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch entries from each RSS URL. Returns list of dicts for raw_items.
    """
    entries_per_feed = entries_per_feed if entries_per_feed is not None else RSS_ENTRIES_PER_FEED
    out: list[dict[str, Any]] = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not getattr(feed, "entries", None):
                logger.debug("RSS parse issue for %s: %s", url, getattr(feed, "bozo_exception", ""))
            for e in (feed.entries or [])[:entries_per_feed]:
                link = e.get("link") or ""
                published = None
                for key in ("published_parsed", "updated_parsed"):
                    val = e.get(key)
                    if val:
                        try:
                            published = datetime.fromtimestamp(time.mktime(val))
                        except Exception:
                            pass
                        break
                summary = e.get("summary") or e.get("description") or ""
                title = e.get("title") or ""
                source_id = e.get("id") or link or f"{url}_{hash((title, link)) % 2**31}"
                if isinstance(source_id, bytes):
                    source_id = source_id.decode("utf-8", errors="replace")
                out.append({
                    "source": "rss",
                    "source_id": str(source_id)[:500],
                    "url": link[:2000] if link else None,
                    "title": (title or "")[:500],
                    "text": (f"{title}\n\n{summary}" or "")[:50000],
                    "author": e.get("author"),
                    "published_at": published,
                    "metadata": {"feed_url": url},
                })
        except Exception as e:
            logger.warning("RSS %s failed: %s", url, e)
    return out
