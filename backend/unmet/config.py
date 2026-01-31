"""Load config from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Prefer backend/.env then repo root .env
_load_order = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
]
for p in _load_order:
    if p.exists():
        load_dotenv(p)
        break


def _str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


# Supabase
SUPABASE_URL = _str("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = _str("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_DB_URL = _str("SUPABASE_DB_URL")

# Gemini
GEMINI_API_KEY = _str("GEMINI_API_KEY")
GEMINI_TEXT_MODEL = _str("GEMINI_TEXT_MODEL") or "gemini-2.0-flash"

# Reddit: PRAW (official API, needs approval) or Apify (no Reddit approval)
REDDIT_CLIENT_ID = _str("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _str("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = _str("REDDIT_USER_AGENT") or "UnmetNewsletter/1.0"
APIFY_API_TOKEN = _str("APIFY_API_TOKEN")
APIFY_REDDIT_ACTOR = _str("APIFY_REDDIT_ACTOR") or "trudax/reddit-scraper"

# Ingest limits (tunable via env)
HN_TOP_LIMIT = _int("HN_TOP_LIMIT", 100)
HN_COMMENTS_LIMIT = _int("HN_COMMENTS_LIMIT", 5)  # top N comments per story (0 = no comments)
REDDIT_POSTS_PER_SUB = _int("REDDIT_POSTS_PER_SUB", 25)
RSS_ENTRIES_PER_FEED = _int("RSS_ENTRIES_PER_FEED", 20)

# Newsletter scope (hard gate: ranking/selection reference this)
NEWSLETTER_AUDIENCE = "B2B builders/devtools founders"
INCLUDED_TOPICS = [
    "devtools",
    "infra",
    "security",
    "data",
    "AI ops",
    "cloud",
    "compliance",
    "SaaS ops",
    "observability",
    "developer productivity",
    "payments infra",
    "platform engineering",
]
EXCLUDED_TOPICS = [
    "local human interest",
    "agriculture/food giveaways",
    "sports",
    "celebrity",
    "lifestyle",
    "pure politics",
]  # unless directly impacts tech compliance/operations

# Pre-cluster: top N candidates by unmet_score (configurable)
EDITOR_GATE_TOP_N = _int("EDITOR_GATE_TOP_N", 50)
