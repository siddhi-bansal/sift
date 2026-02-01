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


def get_sources_for_ingest() -> tuple[list[str], list[str]]:
    """
    Return (subreddits, rss_urls) to ingest from interest_sources.
    Uses all sources with their weight (no subscriber-based weighting).
    """
    sources = fetch_interest_sources()
    if not sources:
        return ([], [])

    agg: dict[tuple[str, str], float] = {}
    for row in sources:
        key = (row["source_type"], (row["source_value"] or "").strip())
        if not key[1]:
            continue
        w = float(row.get("weight") or 1.0)
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


def upsert_raw_item(row: dict[str, Any]) -> str | None:
    """Insert or ignore raw_items. Optional fetched_at, evidence_snippets (list). Backward compatible if evidence_snippets column missing."""
    with get_conn() as conn:
        cur = conn.cursor()
        params = {
            "source": row["source"],
            "source_id": str(row["source_id"]),
            "url": row.get("url"),
            "title": row.get("title") or "",
            "text": (row.get("text") or "")[:100_000],
            "author": row.get("author"),
            "published_at": row.get("published_at"),
            "metadata": psycopg.types.json.Jsonb(row.get("metadata") or {}),
            "fetched_at": row.get("fetched_at"),
        }
        try:
            cur.execute(
                """
                INSERT INTO raw_items (source, source_id, url, title, text, author, published_at, metadata, fetched_at, evidence_snippets)
                VALUES (%(source)s, %(source_id)s, %(url)s, %(title)s, %(text)s, %(author)s, %(published_at)s, %(metadata)s::jsonb, COALESCE(%(fetched_at)s, now()), COALESCE(%(evidence_snippets)s::jsonb, '[]'::jsonb))
                ON CONFLICT (source, source_id) DO UPDATE SET
                  title = EXCLUDED.title, text = EXCLUDED.text, author = EXCLUDED.author,
                  published_at = EXCLUDED.published_at, metadata = EXCLUDED.metadata, fetched_at = COALESCE(EXCLUDED.fetched_at, now())
                RETURNING id::text
                """,
                {**params, "evidence_snippets": psycopg.types.json.Jsonb(row.get("evidence_snippets") or [])},
            )
        except Exception as e:
            if "evidence_snippets" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    INSERT INTO raw_items (source, source_id, url, title, text, author, published_at, metadata, fetched_at)
                    VALUES (%(source)s, %(source_id)s, %(url)s, %(title)s, %(text)s, %(author)s, %(published_at)s, %(metadata)s::jsonb, COALESCE(%(fetched_at)s, now()))
                    ON CONFLICT (source, source_id) DO UPDATE SET
                      title = EXCLUDED.title, text = EXCLUDED.text, author = EXCLUDED.author,
                      published_at = EXCLUDED.published_at, metadata = EXCLUDED.metadata, fetched_at = COALESCE(EXCLUDED.fetched_at, now())
                    RETURNING id::text
                    """,
                    params,
                )
            else:
                raise
        r = cur.fetchone()
        return r["id"] if r else None


def update_raw_item_evidence_snippets(raw_item_id: str, evidence_snippets: list[str]) -> None:
    """Update evidence_snippets for a raw_item. No-op if column does not exist."""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE raw_items SET evidence_snippets = %s::jsonb WHERE id = %s::uuid",
                (psycopg.types.json.Jsonb(evidence_snippets), raw_item_id),
            )
        except Exception as e:
            if "evidence_snippets" in str(e) or "undefined_column" in str(e).lower():
                pass
            else:
                raise


def raw_items_for_date(source_date: str) -> list[dict[str, Any]]:
    """Fetch raw_items that were fetched on the given date (fetch window). Backward compatible if evidence_snippets column missing."""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, source, source_id, url, title, text, author, published_at, metadata, evidence_snippets
                FROM raw_items
                WHERE fetched_at::date = %s::date
                ORDER BY published_at DESC NULLS LAST
                """,
                (source_date,),
            )
            rows = list(cur.fetchall())
        except Exception as e:
            if "evidence_snippets" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    SELECT id, source, source_id, url, title, text, author, published_at, metadata
                    FROM raw_items
                    WHERE fetched_at::date = %s::date
                    ORDER BY published_at DESC NULLS LAST
                    """,
                    (source_date,),
                )
                rows = list(cur.fetchall())
                for r in rows:
                    r["evidence_snippets"] = []
            else:
                raise
        return rows


def upsert_item_label(
    raw_item_id: str,
    label: str,
    confidence: float,
    pain_score: float,
    audience_fit: float | None = None,
    pain_intensity: float | None = None,
    actionability: float | None = None,
    evidence_spans: list[str] | None = None,
    exclude_reason: str | None = None,
    topic_tags: list[str] | None = None,
    claim_anchors: list[str] | None = None,
) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO item_labels (raw_item_id, label, confidence, pain_score, audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason, topic_tags, claim_anchors)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb)
                ON CONFLICT (raw_item_id) DO UPDATE SET
                  label = EXCLUDED.label, confidence = EXCLUDED.confidence, pain_score = EXCLUDED.pain_score,
                  audience_fit = COALESCE(EXCLUDED.audience_fit, item_labels.audience_fit),
                  pain_intensity = COALESCE(EXCLUDED.pain_intensity, item_labels.pain_intensity),
                  actionability = COALESCE(EXCLUDED.actionability, item_labels.actionability),
                  evidence_spans = COALESCE(EXCLUDED.evidence_spans, item_labels.evidence_spans),
                  exclude_reason = EXCLUDED.exclude_reason,
                  topic_tags = COALESCE(EXCLUDED.topic_tags, item_labels.topic_tags),
                  claim_anchors = COALESCE(EXCLUDED.claim_anchors, item_labels.claim_anchors)
                """,
                (
                    raw_item_id,
                    label,
                    confidence,
                    pain_score,
                    audience_fit,
                    pain_intensity,
                    actionability,
                    psycopg.types.json.Jsonb(evidence_spans or []),
                    exclude_reason,
                    psycopg.types.json.Jsonb(topic_tags or []),
                    psycopg.types.json.Jsonb(claim_anchors or []),
                ),
            )
        except Exception as e:
            if "topic_tags" in str(e) or "claim_anchors" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    INSERT INTO item_labels (raw_item_id, label, confidence, pain_score, audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (raw_item_id) DO UPDATE SET
                      label = EXCLUDED.label, confidence = EXCLUDED.confidence, pain_score = EXCLUDED.pain_score,
                      audience_fit = COALESCE(EXCLUDED.audience_fit, item_labels.audience_fit),
                      pain_intensity = COALESCE(EXCLUDED.pain_intensity, item_labels.pain_intensity),
                      actionability = COALESCE(EXCLUDED.actionability, item_labels.actionability),
                      evidence_spans = COALESCE(EXCLUDED.evidence_spans, item_labels.evidence_spans),
                      exclude_reason = EXCLUDED.exclude_reason
                    """,
                    (
                        raw_item_id,
                        label,
                        confidence,
                        pain_score,
                        audience_fit,
                        pain_intensity,
                        actionability,
                        psycopg.types.json.Jsonb(evidence_spans or []),
                        exclude_reason,
                    ),
                )
            elif "audience_fit" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    INSERT INTO item_labels (raw_item_id, label, confidence, pain_score)
                    VALUES (%s::uuid, %s, %s, %s)
                    ON CONFLICT (raw_item_id) DO UPDATE SET label = EXCLUDED.label, confidence = EXCLUDED.confidence, pain_score = EXCLUDED.pain_score
                    """,
                    (raw_item_id, label, confidence, pain_score),
                )
            else:
                raise


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
    """Return raw_item_id -> {label, confidence, pain_score, audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason, topic_tags, claim_anchors} for given ids. Backward compatible if new columns missing."""
    if not raw_item_ids:
        return {}
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT raw_item_id::text, label, confidence, pain_score, audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason, topic_tags, claim_anchors
                FROM item_labels WHERE raw_item_id = ANY(%s::uuid[])
                """,
                (raw_item_ids,),
            )
        except Exception as e:
            if "topic_tags" in str(e) or "claim_anchors" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    SELECT raw_item_id::text, label, confidence, pain_score, audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason
                    FROM item_labels WHERE raw_item_id = ANY(%s::uuid[])
                    """,
                    (raw_item_ids,),
                )
            elif "audience_fit" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    "SELECT raw_item_id::text, label, confidence, pain_score FROM item_labels WHERE raw_item_id = ANY(%s::uuid[])",
                    (raw_item_ids,),
                )
            else:
                raise
        out: dict[str, dict[str, Any]] = {}
        for r in cur.fetchall():
            row = {
                "label": r["label"],
                "confidence": float(r["confidence"] or 0),
                "pain_score": float(r["pain_score"] or 0),
                "audience_fit": float(r["audience_fit"]) if r.get("audience_fit") is not None else None,
                "pain_intensity": float(r["pain_intensity"]) if r.get("pain_intensity") is not None else None,
                "actionability": float(r["actionability"]) if r.get("actionability") is not None else None,
                "evidence_spans": list(r["evidence_spans"]) if r.get("evidence_spans") else [],
                "exclude_reason": r.get("exclude_reason"),
            }
            if r.get("topic_tags") is not None:
                row["topic_tags"] = list(r["topic_tags"]) if r["topic_tags"] else []
            else:
                row["topic_tags"] = []
            if r.get("claim_anchors") is not None:
                row["claim_anchors"] = list(r["claim_anchors"]) if r["claim_anchors"] else []
            else:
                row["claim_anchors"] = []
            out[r["raw_item_id"]] = row
        return out


def delete_catalysts_for_date(date: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM catalyst_items WHERE date = %s::date", (date,))


def insert_catalyst(
    date: str,
    title: str,
    summary: str,
    interests: list[str],
    problems_created: str,
    source_urls: list[str],
    what_changed: str | None = None,
    who_feels_it: str | None = None,
    opportunity_wedge: str | None = None,
    confidence: float | None = None,
) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO catalyst_items (date, title, summary, interests, problems_created, source_urls, what_changed, who_feels_it, opportunity_wedge, confidence)
                VALUES (%s::date, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    date,
                    title,
                    summary,
                    psycopg.types.json.Jsonb(interests),
                    problems_created or "",
                    psycopg.types.json.Jsonb(source_urls),
                    what_changed,
                    who_feels_it,
                    opportunity_wedge,
                    confidence,
                ),
            )
        except Exception as e:
            if "what_changed" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    INSERT INTO catalyst_items (date, title, summary, interests, problems_created, source_urls)
                    VALUES (%s::date, %s, %s, %s::jsonb, %s, %s::jsonb)
                    """,
                    (date, title, summary, psycopg.types.json.Jsonb(interests), problems_created or "", psycopg.types.json.Jsonb(source_urls)),
                )
            else:
                raise


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
        try:
            cur.execute(
                """
                SELECT title, summary, interests, problems_created, source_urls, what_changed, who_feels_it, opportunity_wedge, confidence
                FROM catalyst_items WHERE date = %s::date ORDER BY id
                """,
                (date,),
            )
        except Exception as e:
            if "what_changed" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    "SELECT title, summary, interests, problems_created, source_urls FROM catalyst_items WHERE date = %s::date ORDER BY id",
                    (date,),
                )
            else:
                raise
        rows = list(cur.fetchall())
        for r in rows:
            if "what_changed" not in r:
                r["what_changed"] = None
            if "who_feels_it" not in r:
                r["who_feels_it"] = None
            if "opportunity_wedge" not in r:
                r["opportunity_wedge"] = None
            if "confidence" not in r:
                r["confidence"] = None
        return rows


def get_previous_day_clusters(date: str) -> list[dict[str, Any]]:
    """Clusters from the previous calendar day for trend/rising comparison."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, summary, top_terms, example_urls FROM clusters WHERE date = (%s::date - interval '1 day') ORDER BY score DESC",
            (date,),
        )
        return list(cur.fetchall())
