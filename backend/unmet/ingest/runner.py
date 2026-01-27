"""Run full ingest for a date: HN + Reddit + RSS -> raw_items."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from .. import db
from ..config import APIFY_API_TOKEN
from .hn import fetch_hn_stories
from .reddit_apify import fetch_reddit_via_apify
from .reddit_ingest import fetch_reddit_posts
from .rss_ingest import fetch_rss_items

logger = logging.getLogger(__name__)


def run_ingest(target_date: str | None = None) -> int:
    """
    Run ingest for target_date (YYYY-MM-DD). Uses today if not set.
    Sets fetched_at to that date so analyze --date uses these items.
    Returns count of items written.
    """
    d = target_date or str(date.today())
    fetched_dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    counts = {"hn": 0, "reddit": 0, "rss": 0}
    subscriber_counts = db.get_subscriber_interest_counts()
    subreddits, rss_urls = db.get_sources_for_ingest(subscriber_counts if subscriber_counts else None)

    def add_fetched(r: dict) -> dict:
        r = dict(r)
        r["fetched_at"] = fetched_dt
        return r

    # HN: always ingest (no interest mapping)
    try:
        for row in fetch_hn_stories():
            rid = db.upsert_raw_item(add_fetched(row))
            if rid:
                counts["hn"] += 1
    except Exception as e:
        logger.exception("HN ingest failed: %s", e)

    # Reddit: Apify (no Reddit approval) if APIFY_API_TOKEN set, else PRAW
    if subreddits:
        try:
            if APIFY_API_TOKEN:
                rows = fetch_reddit_via_apify(subreddits)
            else:
                rows = fetch_reddit_posts(subreddits)
            for row in rows:
                rid = db.upsert_raw_item(add_fetched(row))
                if rid:
                    counts["reddit"] += 1
        except Exception as e:
            logger.exception("Reddit ingest failed: %s", e)

    # RSS
    if rss_urls:
        try:
            for row in fetch_rss_items(rss_urls):
                rid = db.upsert_raw_item(add_fetched(row))
                if rid:
                    counts["rss"] += 1
        except Exception as e:
            logger.exception("RSS ingest failed: %s", e)

    logger.info("Ingest for %s: hn=%s reddit=%s rss=%s", d, counts["hn"], counts["reddit"], counts["rss"])
    return counts["hn"] + counts["reddit"] + counts["rss"]
