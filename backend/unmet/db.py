"""Database client using Supabase Postgres (psycopg)."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row

from .config import SUPABASE_DB_URL

logger = logging.getLogger(__name__)


def get_connection_string() -> str:
    url = SUPABASE_DB_URL or ""
    if not url:
        logger.warning("SUPABASE_DB_URL is not set")
    return url


@contextmanager
def get_conn() -> Generator[psycopg.Connection, None, None]:
    """Yield a connection with dict_row. Caller uses conn.cursor() and must commit or rollback."""
    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_many(
    sql: str, params_list: list[tuple[Any, ...]] | list[dict[str, Any]]
) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        if params_list and isinstance(params_list[0], dict):
            cur.executemany(sql, params_list)
        else:
            cur.executemany(sql, params_list or [])


def fetch_interests() -> list[dict[str, Any]]:
    """Return all interests from DB."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description FROM interests ORDER BY name")
        return list(cur.fetchall())


def fetch_interest_sources() -> list[dict[str, Any]]:
    """Return all interest_sources with interest name for convenience."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.interest_id, i.name AS interest_name, s.source_type, s.source_value, s.weight
            FROM interest_sources s
            JOIN interests i ON i.id = s.interest_id
            ORDER BY s.source_type, s.source_value
            """
        )
        return list(cur.fetchall())


def get_sources_for_ingest(
    subscriber_interest_counts: dict[str, int] | None,
) -> tuple[list[str], list[str]]:
    """
    Return (subreddits, rss_urls) to ingest.
    If subscriber_interest_counts is None or empty, use 'General' interest only.
    Otherwise weight sources by how many subscribers have each interest.
    """
    sources = fetch_interest_sources()
    if not sources:
        return ([], [])

    # Build interest_id -> name and name -> weight from subscribers
    interest_weights: dict[str, float] = {}
    if subscriber_interest_counts:
        for name, count in subscriber_interest_counts.items():
            interest_weights[name] = float(count)
    else:
        # Fallback: General only (by name)
        general = next((s for s in sources if s.get("interest_name") == "General"), None)
        if general:
            interest_weights["General"] = 1.0
        else:
            # No General: use first interest with weight 1
            names = {s["interest_name"] for s in sources}
            if names:
                interest_weights[next(iter(names))] = 1.0

    # Aggregate (source_type, source_value) -> sum(weight)
    agg: dict[tuple[str, str], float] = {}
    for row in sources:
        name = row["interest_name"]
        w = interest_weights.get(name, 0.0) * float(row.get("weight") or 1.0)
        if w <= 0:
            continue
        key = (row["source_type"], row["source_value"].strip())
        agg[key] = agg.get(key, 0) + w

    subreddits = sorted(
        {v for (st, v) in agg if st == "subreddit"},
        key=lambda x: -agg[("subreddit", x)],
    )
    rss_urls = sorted(
        {v for (st, v) in agg if st == "rss"},
        key=lambda x: -agg[("rss", x)],
    )
    return (subreddits, rss_urls)


def get_subscriber_interest_counts() -> dict[str, int]:
    """Return map interest_name -> count of subscribers who selected it."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.name, COUNT(si.subscriber_id) AS c
            FROM interests i
            LEFT JOIN subscriber_interests si ON si.interest_id = i.id
            GROUP BY i.id, i.name
            HAVING COUNT(si.subscriber_id) > 0
            """
        )
        return {row["name"]: row["c"] for row in cur.fetchall()}


def upsert_raw_item(row: dict[str, Any]) -> str | None:
    """Insert or ignore raw_items. Optional 'fetched_at' in row overrides default now()."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO raw_items (source, source_id, url, title, text, author, published_at, metadata, fetched_at)
            VALUES (%(source)s, %(source_id)s, %(url)s, %(title)s, %(text)s, %(author)s, %(published_at)s, %(metadata)s::jsonb, COALESCE(%(fetched_at)s, now()))
            ON CONFLICT (source, source_id) DO UPDATE SET
              title = EXCLUDED.title, text = EXCLUDED.text, author = EXCLUDED.author,
              published_at = EXCLUDED.published_at, metadata = EXCLUDED.metadata, fetched_at = COALESCE(EXCLUDED.fetched_at, now())
            RETURNING id::text
            """,
            {
                "source": row["source"],
                "source_id": str(row["source_id"]),
                "url": row.get("url"),
                "title": row.get("title") or "",
                "text": (row.get("text") or "")[:100_000],
                "author": row.get("author"),
                "published_at": row.get("published_at"),
                "metadata": psycopg.types.json.Jsonb(row.get("metadata") or {}),
                "fetched_at": row.get("fetched_at"),
            },
        )
        r = cur.fetchone()
        return r["id"] if r else None


def raw_items_for_date(source_date: str) -> list[dict[str, Any]]:
    """Fetch raw_items that were fetched on the given date (fetch window)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, source, source_id, url, title, text, author, published_at, metadata
            FROM raw_items
            WHERE fetched_at::date = %s::date
            ORDER BY published_at DESC NULLS LAST
            """,
            (source_date,),
        )
        return list(cur.fetchall())


def upsert_item_label(raw_item_id: str, label: str, confidence: float, pain_score: float) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO item_labels (raw_item_id, label, confidence, pain_score)
            VALUES (%s::uuid, %s, %s, %s)
            ON CONFLICT (raw_item_id) DO UPDATE SET label = EXCLUDED.label, confidence = EXCLUDED.confidence, pain_score = EXCLUDED.pain_score
            """,
            (raw_item_id, label, confidence, pain_score),
        )


def save_embedding(raw_item_id: str, embedding: list[float], model: str = "gemini-embedding-001") -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO item_embeddings (raw_item_id, embedding, model)
            VALUES (%s::uuid, %s, %s)
            ON CONFLICT (raw_item_id) DO UPDATE SET embedding = EXCLUDED.embedding, model = EXCLUDED.model
            """,
            (raw_item_id, embedding, model),
        )


def get_embeddings_for_ids(raw_item_ids: list[str]) -> dict[str, list[float]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT raw_item_id::text, embedding FROM item_embeddings WHERE raw_item_id = ANY(%s::uuid[])",
            (raw_item_ids,),
        )
        return {r["raw_item_id"]: r["embedding"] for r in cur.fetchall()}


def insert_cluster(
    date: str,
    cluster_index: int,
    title: str,
    summary: str,
    persona: str,
    why_matters: str,
    size: int,
    score: float,
    top_terms: list[str],
    example_urls: list[str],
) -> str:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clusters (date, cluster_index, title, summary, persona, why_matters, size, score, top_terms, example_urls)
            VALUES (%s::date, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id::text
            """,
            (date, cluster_index, title, summary, persona, why_matters, size, score, top_terms, psycopg.types.json.Jsonb(example_urls)),
        )
        r = cur.fetchone()
        return r["id"]


def insert_cluster_item(cluster_id: str, raw_item_id: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cluster_items (cluster_id, raw_item_id) VALUES (%s::uuid, %s::uuid) ON CONFLICT (cluster_id, raw_item_id) DO NOTHING",
            (cluster_id, raw_item_id),
        )


def update_cluster(cluster_id: str, title: str, summary: str, persona: str, why_matters: str, example_urls: list[str] | None = None) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        if example_urls is not None:
            cur.execute(
                "UPDATE clusters SET title = %s, summary = %s, persona = %s, why_matters = %s, example_urls = %s::jsonb WHERE id = %s::uuid",
                (title, summary, persona, why_matters, psycopg.types.json.Jsonb(example_urls), cluster_id),
            )
        else:
            cur.execute(
                "UPDATE clusters SET title = %s, summary = %s, persona = %s, why_matters = %s WHERE id = %s::uuid",
                (title, summary, persona, why_matters, cluster_id),
            )


def get_item_labels_for_raw_ids(raw_item_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Return raw_item_id -> {label, confidence, pain_score} for given ids."""
    if not raw_item_ids:
        return {}
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT raw_item_id::text, label, confidence, pain_score FROM item_labels WHERE raw_item_id = ANY(%s::uuid[])",
            (raw_item_ids,),
        )
        return {r["raw_item_id"]: {"label": r["label"], "confidence": r["confidence"], "pain_score": float(r["pain_score"] or 0)} for r in cur.fetchall()}


def delete_catalysts_for_date(date: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM catalyst_items WHERE date = %s::date", (date,))


def insert_catalyst(date: str, title: str, summary: str, interests: list[str], problems_created: str, source_urls: list[str]) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO catalyst_items (date, title, summary, interests, problems_created, source_urls)
            VALUES (%s::date, %s, %s, %s::jsonb, %s, %s::jsonb)
            """,
            (date, title, summary, psycopg.types.json.Jsonb(interests), problems_created or "", psycopg.types.json.Jsonb(source_urls)),
        )


def upsert_daily_report(date: str, markdown_content: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO daily_reports (date, markdown_content, generated_at)
            VALUES (%s::date, %s, now())
            ON CONFLICT (date) DO UPDATE SET markdown_content = EXCLUDED.markdown_content, generated_at = now()
            """,
            (date, markdown_content),
        )


def get_daily_report(date: str) -> str | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT markdown_content FROM daily_reports WHERE date = %s::date", (date,))
        r = cur.fetchone()
        return r["markdown_content"] if r else None


def delete_clusters_for_date(date: str) -> None:
    """Delete clusters (and cluster_items via FK) for the given date."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM clusters WHERE date = %s::date", (date,))


def get_clusters_for_date(date: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, date, cluster_index, title, summary, persona, why_matters, size, score, top_terms, example_urls
            FROM clusters WHERE date = %s::date ORDER BY cluster_index
            """,
            (date,),
        )
        return list(cur.fetchall())


def get_catalysts_for_date(date: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT title, summary, interests, problems_created, source_urls FROM catalyst_items WHERE date = %s::date ORDER BY id",
            (date,),
        )
        return list(cur.fetchall())


def get_previous_day_clusters(date: str) -> list[dict[str, Any]]:
    """Clusters from the previous calendar day for trend/rising comparison."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, summary, top_terms, example_urls FROM clusters WHERE date = (%s::date - interval '1 day') ORDER BY score DESC",
            (date,),
        )
        return list(cur.fetchall())
