"""Run analyze for a date: classify_and_score, filter, editor gate, cluster selected items -> clusters + cluster_items."""
from __future__ import annotations

import logging
import time
from typing import Any

from .. import db
from ..gemini_client import classify_and_score_item, editor_gate_selection, embed_batch_with_retry
from .clustering import cluster_with_embeddings, cluster_with_tfidf, top_terms_tfidf
from .evidence_snippets import extract_evidence_snippets
from .pain_score import pain_score_heuristic
from .scoring import filter_and_rank_candidates

logger = logging.getLogger(__name__)


def run_analyze(target_date: str | None = None) -> None:
    """
    Run analyze for target_date (YYYY-MM-DD).
    1) classify_and_score_item per item -> item_labels (with audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason)
    2) Deterministic filter + rank; keep top N candidates
    3) Editor gate (one Gemini call): select featured_pain_ids, secondary_pain_ids, catalyst_ids
    4) Only cluster items in featured + secondary pain ids
    5) Embed (with resilience) or TF-IDF, cluster
    6) Insert clusters + cluster_items
    """
    from datetime import date
    d = target_date or str(date.today())

    db.delete_clusters_for_date(d)
    items = db.raw_items_for_date(d)
    if not items:
        logger.warning("No raw_items for date %s", d)
        return

    # 1) Classify and score per item
    for i, row in enumerate(items):
        rid = str(row["id"])
        title = (row.get("title") or "")[:500]
        text = (row.get("text") or "")[:8000]
        heuristic = pain_score_heuristic(text, title)
        try:
            out = classify_and_score_item(text, title)
        except Exception as e:
            logger.warning("classify_and_score failed for %s: %s", rid, e)
            out = {
                "label": "OTHER",
                "confidence": 0.0,
                "audience_fit": 0.0,
                "pain_intensity": 0.0,
                "actionability": 0.0,
                "evidence_spans": [],
                "exclude_reason": "error",
            }
        label = out["label"]
        conf = out["confidence"]
        pain = heuristic * 0.5 + (0.5 if label == "PAIN" else 0.3 if label == "DISCUSSION" else 0) * conf
        db.upsert_item_label(
            rid,
            label,
            conf,
            pain,
            audience_fit=out.get("audience_fit"),
            pain_intensity=out.get("pain_intensity"),
            actionability=out.get("actionability"),
            evidence_spans=out.get("evidence_spans"),
            exclude_reason=out.get("exclude_reason"),
            topic_tags=out.get("topic_tags"),
            claim_anchors=out.get("claim_anchors"),
        )
        if (i + 1) % 20 == 0:
            time.sleep(0.5)

    ids = [str(r["id"]) for r in items]
    labels_map = db.get_item_labels_for_raw_ids(ids)

    # 1b) For PAIN/DISCUSSION items, generate evidence_snippets from title + text + HN comments
    for row in items:
        rid = str(row["id"])
        lab = labels_map.get(rid, {})
        if lab.get("label") not in ("PAIN", "DISCUSSION"):
            continue
        try:
            snippets = extract_evidence_snippets(row)
            if snippets:
                db.update_raw_item_evidence_snippets(rid, snippets)
        except Exception as e:
            logger.debug("evidence_snippets for %s: %s", rid, e)

    # 2) Filter + rank to top N candidates
    candidates = filter_and_rank_candidates(items, labels_map)
    logger.info("Filter: %d items -> %d candidates (top N by unmet_score)", len(items), len(candidates))

    if not candidates:
        logger.warning("No candidates passed filter for %s", d)
        return

    # 3) Editor gate: one Gemini call
    gate_input = [
        {
            "id": str(r["id"]),
            "title": r.get("title"),
            "url": r.get("url"),
            "label": (labels_map.get(str(r["id"])) or {}).get("label"),
            "confidence": (labels_map.get(str(r["id"])) or {}).get("confidence"),
            "audience_fit": (labels_map.get(str(r["id"])) or {}).get("audience_fit"),
            "pain_intensity": (labels_map.get(str(r["id"])) or {}).get("pain_intensity"),
            "actionability": (labels_map.get(str(r["id"])) or {}).get("actionability"),
            "evidence_spans": (labels_map.get(str(r["id"])) or {}).get("evidence_spans") or [],
            "topic_tags": (labels_map.get(str(r["id"])) or {}).get("topic_tags") or [],
            "claim_anchors": (labels_map.get(str(r["id"])) or {}).get("claim_anchors") or [],
        }
        for r in candidates
    ]
    gate = editor_gate_selection(gate_input)
    featured_ids = set(gate.get("featured_pain_ids") or [])
    secondary_ids = set(gate.get("secondary_pain_ids") or [])
    pain_ids_to_cluster = featured_ids | secondary_ids
    rejects = gate.get("rejects") or []
    logger.info(
        "Editor gate: featured=%d secondary=%d catalyst_ids=%d rejects=%d",
        len(featured_ids),
        len(secondary_ids),
        len(gate.get("catalyst_ids") or []),
        len(rejects),
    )
    for r in rejects[:10]:
        logger.info("  Reject id=%s reason=%s", r.get("id"), r.get("reason"))

    # 4) Only cluster items in featured + secondary
    id_to_item = {str(r["id"]): r for r in items}
    pain_items = [id_to_item[rid] for rid in pain_ids_to_cluster if rid in id_to_item]
    if not pain_items:
        logger.warning("No pain items selected by editor gate for %s", d)
        return

    # 5) Embed (subprocess + retry) or TF-IDF fallback
    texts = [(r.get("title") or "") + " " + (r.get("text") or "") for r in pain_items]
    embs = embed_batch_with_retry(texts, use_subprocess=True)
    if embs and len(embs) == len(texts):
        try:
            for j, r in enumerate(pain_items):
                db.save_embedding(str(r["id"]), embs[j])
            time.sleep(0.2)
        except Exception as e:
            logger.warning("Saving embeddings failed: %s", e)
            embs = None
    else:
        if texts:
            logger.info("Embeddings failed or unavailable; using TF-IDF for clustering.")
        embs = None

    if embs and len(embs) == len(pain_items):
        clusters_idx = cluster_with_embeddings(pain_items, embs)
    else:
        clusters_idx = cluster_with_tfidf(pain_items)

    # 6) Insert clusters + cluster_items
    for ci, cluster_indices in enumerate(clusters_idx):
        cluster_items_sub = [pain_items[i] for i in cluster_indices]
        texts_sub = [texts[i] for i in cluster_indices]
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
