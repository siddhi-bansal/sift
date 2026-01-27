"""Run analyze for a date: pain score, label, cluster PAIN/DISCUSSION -> clusters + cluster_items."""
from __future__ import annotations

import logging
import time
from typing import Any

from .. import db
from ..gemini_client import classify_pain_label, embed_batch
from .clustering import cluster_with_embeddings, cluster_with_tfidf, top_terms_tfidf
from .pain_score import pain_score_heuristic

logger = logging.getLogger(__name__)


def run_analyze(target_date: str | None = None) -> None:
    """
    Run analyze for target_date (YYYY-MM-DD).
    1) Heuristic pain score + Gemini label per item -> item_labels
    2) Keep PAIN/DISCUSSION only
    3) Embed (Gemini) or TF-IDF, cluster
    4) Insert clusters + cluster_items with top_terms, example_urls, placeholder title/summary
    """
    from datetime import date
    d = target_date or str(date.today())

    db.delete_clusters_for_date(d)
    items = db.raw_items_for_date(d)
    if not items:
        logger.warning("No raw_items for date %s", d)
        return

    # 1) Pain score + Gemini label per item
    for i, row in enumerate(items):
        rid = str(row["id"])
        title = (row.get("title") or "")[:500]
        text = (row.get("text") or "")[:8000]
        heuristic = pain_score_heuristic(text, title)
        try:
            label, conf = classify_pain_label(text, title)
        except Exception as e:
            logger.warning("classify failed for %s: %s", rid, e)
            label, conf = "OTHER", 0.0
        pain = heuristic * 0.5 + (0.5 if label == "PAIN" else 0.3 if label == "DISCUSSION" else 0) * conf
        db.upsert_item_label(rid, label, conf, pain)
        if (i + 1) % 20 == 0:
            time.sleep(0.5)

    # 2) Filter to PAIN/DISCUSSION
    ids = [str(r["id"]) for r in items]
    labels_map = db.get_item_labels_for_raw_ids(ids)
    pain_indices = [i for i, r in enumerate(items) if labels_map.get(str(r["id"]), {}).get("label") in ("PAIN", "DISCUSSION")]
    pain_items = [items[i] for i in pain_indices]
    if not pain_items:
        logger.warning("No PAIN/DISCUSSION items for %s", d)
        return

    # 3) Embed or TF-IDF, then cluster
    texts = [(r.get("title") or "") + " " + (r.get("text") or "") for r in pain_items]
    embs: list[list[float]] | None = None
    try:
        embs = embed_batch(texts)
        if embs and len(embs) == len(texts):
            for j, r in enumerate(pain_items):
                db.save_embedding(str(r["id"]), embs[j])
            time.sleep(0.2)
    except Exception as e:
        logger.info("Embeddings skipped, using TF-IDF: %s", e)
        embs = None

    if embs and len(embs) == len(pain_items):
        clusters_idx = cluster_with_embeddings(pain_items, embs)
    else:
        clusters_idx = cluster_with_tfidf(pain_items)

    # 4) Insert clusters + cluster_items
    for ci, cluster_indices in enumerate(clusters_idx):
        cluster_items_sub = [pain_items[i] for i in cluster_indices]
        texts_sub = [texts[pain_indices[i]] for i in cluster_indices]
        top_terms = top_terms_tfidf(texts_sub, k=5)
        urls = []
        for r in cluster_items_sub:
            u = r.get("url")
            if u and u not in urls:
                urls.append(u)
        example_urls = urls[:5]
        title_placeholder = (top_terms[0] or "Pain cluster")[:200]
        size = len(cluster_items_sub)
        scores = [labels_map.get(str(r["id"]), {}).get("pain_score", 0) for r in cluster_items_sub]
        score = sum(scores) / len(scores) if scores else 0
        cid = db.insert_cluster(
            date=d,
            cluster_index=ci,
            title=title_placeholder,
            summary="",
            persona="",
            why_matters="",
            size=size,
            score=round(score, 2),
            top_terms=top_terms[:10],
            example_urls=example_urls,
        )
        for r in cluster_items_sub:
            db.insert_cluster_item(cid, str(r["id"]))
    logger.info("Analyze for %s: %d pain items -> %d clusters", d, len(pain_items), len(clusters_idx))
