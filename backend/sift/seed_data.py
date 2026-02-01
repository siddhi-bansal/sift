"""Seed interests and interest_sources (sources for ingest). No per-subscriber interests."""
from __future__ import annotations

import logging
from typing import Any

from . import db

logger = logging.getLogger(__name__)

# Same logical data as supabase/seed.sql — keep in sync or run seed.sql instead
INTERESTS = [
    ("General", "Broad tech and product signals"),
    ("Developer Tools", "IDEs, CLIs, dev experience, debugging"),
    ("AI / ML", "Machine learning, LLMs, AI products"),
    ("SaaS & B2B", "B2B software, enterprise, pricing"),
    ("Startups", "Founder pain, fundraising, growth"),
    ("Design & UX", "Design systems, user research, accessibility"),
    ("Data & Infra", "Databases, data pipelines, infrastructure"),
    ("Security & Compliance", "Security, privacy, compliance"),
    ("Marketing", "Growth, SEO, content, ads"),
    ("Mobile", "iOS, Android, cross-platform"),
]

# (interest_name, source_type, source_value, weight)
SOURCES = [
    ("General", "subreddit", "technology", 1.0),
    ("General", "rss", "https://news.ycombinator.com/rss", 1.0),
    ("Developer Tools", "subreddit", "programming", 1.0),
    ("Developer Tools", "subreddit", "vscode", 1.0),
    ("Developer Tools", "subreddit", "devops", 1.0),
    ("Developer Tools", "rss", "https://blog.jetbrains.com/feed/", 0.8),
    ("AI / ML", "subreddit", "MachineLearning", 1.0),
    ("AI / ML", "subreddit", "LocalLLaMA", 1.0),
    ("AI / ML", "rss", "https://blog.google/technology/developers/feed/", 0.9),
    ("SaaS & B2B", "subreddit", "SaaS", 1.0),
    ("SaaS & B2B", "subreddit", "startups", 0.9),
    ("SaaS & B2B", "rss", "https://www.saastr.com/feed/", 0.8),
    ("Startups", "subreddit", "startups", 1.0),
    ("Startups", "subreddit", "entrepreneur", 0.9),
    ("Startups", "rss", "https://www.ycombinator.com/blog/feed/", 0.9),
    ("Design & UX", "subreddit", "UXDesign", 1.0),
    ("Design & UX", "subreddit", "userexperience", 1.0),
    ("Data & Infra", "subreddit", "dataengineering", 1.0),
    ("Data & Infra", "subreddit", "aws", 0.9),
    ("Data & Infra", "rss", "https://aws.amazon.com/blogs/aws/feed/", 0.8),
    ("Security & Compliance", "subreddit", "netsec", 1.0),
    ("Security & Compliance", "subreddit", "cybersecurity", 1.0),
    ("Marketing", "subreddit", "SEO", 1.0),
    ("Marketing", "subreddit", "marketing", 1.0),
    ("Mobile", "subreddit", "iOSProgramming", 1.0),
    ("Mobile", "subreddit", "androiddev", 1.0),
]


def run_seed() -> None:
    """Insert interests and interest_sources. Idempotent via ON CONFLICT / unique checks."""
    with db.get_conn() as conn:
        cur = conn.cursor()
        for name, desc in INTERESTS:
            cur.execute(
                "INSERT INTO interests (name, description) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description",
                (name, desc),
            )
        # Resolve interest_id by name
        cur.execute("SELECT id, name FROM interests")
        by_name = {r["name"]: str(r["id"]) for r in cur.fetchall()}
        for iname, stype, sval, weight in SOURCES:
            iid = by_name.get(iname)
            if not iid:
                continue
            cur.execute(
                """
                INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (interest_id, source_type, source_value) DO UPDATE SET weight = EXCLUDED.weight
                """,
                (iid, stype, sval, weight),
            )
    logger.info("Seeded %d interests and %d sources", len(INTERESTS), len(SOURCES))
