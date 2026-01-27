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

# Reddit (PRAW)
REDDIT_CLIENT_ID = _str("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _str("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = _str("REDDIT_USER_AGENT") or "UnmetNewsletter/1.0"

# Ingest limits (tunable via env)
HN_TOP_LIMIT = _int("HN_TOP_LIMIT", 100)
HN_COMMENTS_LIMIT = _int("HN_COMMENTS_LIMIT", 0)  # 0 = no comments
REDDIT_POSTS_PER_SUB = _int("REDDIT_POSTS_PER_SUB", 25)
RSS_ENTRIES_PER_FEED = _int("RSS_ENTRIES_PER_FEED", 20)
