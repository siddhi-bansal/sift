"""Run report for a date: summarize clusters, coherence gate, idea cards, build markdown, write daily_reports + /out/YYYY-MM-DD.md."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from .. import db
from ..analyze.topic_coherence import validate_topic_coherence
from ..gemini_client import catalyst_bullets, compose_idea_cards, rename_to_match_evidence, summarize_cluster
from ..newsletter_style import (
    format_idea_card,
    get_intro,
    get_todays_themes_from_idea_cards,
)

logger = logging.getLogger(__name__)


def _cluster_items_for_date(date_str: str) -> dict[str, list[dict[str, Any]]]:
    """Return cluster_id -> list of raw_items in that cluster. Backward compatible if evidence_snippets missing."""
    with db.get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT c.id::text AS cluster_id, r.id, r.title, r.text, r.url, r.source, r.evidence_snippets
                FROM clusters c
                JOIN cluster_items ci ON ci.cluster_id = c.id
                JOIN raw_items r ON r.id = ci.raw_item_id
                WHERE c.date = %s::date
                ORDER BY c.cluster_index, r.published_at DESC NULLS LAST
                """,
                (date_str,),
            )
        except Exception as e:
            if "evidence_snippets" in str(e) or "undefined_column" in str(e).lower():
                conn.rollback()
                cur.execute(
                    """
                    SELECT c.id::text AS cluster_id, r.id, r.title, r.text, r.url, r.source
                    FROM clusters c
                    JOIN cluster_items ci ON ci.cluster_id = c.id
                    JOIN raw_items r ON r.id = ci.raw_item_id
                    WHERE c.date = %s::date
                    ORDER BY c.cluster_index, r.published_at DESC NULLS LAST
                    """,
                    (date_str,),
                )
            else:
                raise
        rows = cur.fetchall()
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        cid = r["cluster_id"]
        if cid not in out:
            out[cid] = []
        row = {"id": r["id"], "title": r["title"], "text": r["text"], "url": r["url"], "source": r["source"]}
        if r.get("evidence_snippets") is not None:
            row["evidence_snippets"] = list(r["evidence_snippets"]) if r["evidence_snippets"] else []
        else:
            row["evidence_snippets"] = []
        out[cid].append(row)
    return out


def _catalyst_dedupe_by_topic(catalysts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Avoid overlapping topic_tags unless connects_to adds a new sub-angle."""
    seen_tags: set[str] = set()
    out: list[dict[str, Any]] = []
    for cat in catalysts:
        tags = set((t or "").lower().strip() for t in (cat.get("topic_tags") or [])[:5] if t)
        overlap = tags & seen_tags
        if overlap and not (cat.get("connects_to") or "").strip():
            continue
        seen_tags |= tags
        out.append(cat)
    return out


def run_report(target_date: str | None = None) -> str:
    """
    Run report for target_date: summarize clusters, coherence gate, idea cards, build markdown.
    Writes to daily_reports and /out/YYYY-MM-DD.md. Returns markdown string.
    """
    d = target_date or str(date.today())

    # 1) Summarize each cluster with Gemini
    clusters = db.get_clusters_for_date(d)
    items_by_cluster = _cluster_items_for_date(d)
    all_cluster_item_ids = [str(it["id"]) for items in items_by_cluster.values() for it in items]
    labels = db.get_item_labels_for_raw_ids(all_cluster_item_ids) if all_cluster_item_ids else {}

    for c in clusters:
        cid = str(c["id"])
        items = items_by_cluster.get(cid, [])
        snippets = [f"{x.get('title','')}\n{(x.get('text') or '')[:400]}" for x in items[:15]]
        example_links = [x.get("url") for x in items if x.get("url")][:5]
        try:
            out = summarize_cluster(
                title=c.get("title") or "",
                summary=c.get("summary") or "",
                persona=c.get("persona") or "",
                why_matters=c.get("why_matters") or "",
                example_links=example_links,
                item_snippets=snippets,
            )
            urls = out.get("example_urls") or example_links[:5]
            why = out.get("why_matters") or " ".join(out.get("stakes") or [])[:500]
            db.update_cluster(cid, out["title"], out["summary"], out["persona"], why, urls)
        except Exception as e:
            logger.warning("summarize_cluster failed for %s: %s", cid, e)

    # 2) Evidence-topic coherence gate: validate each cluster; rename or drop
    clusters = db.get_clusters_for_date(d)
    clusters_passed: list[dict[str, Any]] = []
    for c in clusters:
        cid = str(c["id"])
        items = items_by_cluster.get(cid, [])
        topic_tags: list[str] = []
        for it in items:
            topic_tags.extend(labels.get(str(it["id"]), {}).get("topic_tags") or [])
        evidence_snippets = [s for it in items for s in (it.get("evidence_snippets") or [])]
        title = c.get("title") or ""
        passed, reason = validate_topic_coherence(title, topic_tags, evidence_snippets)
        if passed:
            logger.info("coherence pass cluster_id=%s title=%s reason=%s", cid, title[:60], reason)
            clusters_passed.append(c)
            continue
        new_title = rename_to_match_evidence(title, evidence_snippets)
        db.update_cluster(cid, new_title, c.get("summary") or "", c.get("persona") or "", c.get("why_matters") or "", c.get("example_urls") or [])
        passed2, reason2 = validate_topic_coherence(new_title, topic_tags, evidence_snippets)
        if passed2:
            logger.info("coherence pass after rename cluster_id=%s new_title=%s reason=%s", cid, new_title[:60], reason2)
            c = {**c, "title": new_title}
            clusters_passed.append(c)
        else:
            logger.info("coherence fail dropped cluster_id=%s reason=%s", cid, reason)

    # 3) Editor gate penalty: skip clusters with "unclear from evidence" / "not enough evidence"
    clusters_for_cards = [
        c for c in clusters_passed
        if "unclear from evidence" not in (c.get("summary") or "").lower()
        and "not enough evidence" not in (c.get("summary") or "").lower()
    ]

    # 4) Catalyst bullets from RSS/news (replace previous catalysts for this date)
    db.delete_catalysts_for_date(d)
    all_items = db.raw_items_for_date(d)
    all_labels = db.get_item_labels_for_raw_ids([str(r["id"]) for r in all_items])
    news_items = [
        {"title": r.get("title"), "url": r.get("url"), "text": (r.get("text") or "")[:800]}
        for r in all_items
        if r.get("source") == "rss" or all_labels.get(str(r["id"]), {}).get("label") == "NEWS"
    ]
    catalysts = catalyst_bullets(news_items, max_bullets=7)
    for cat in catalysts:
        problems = cat.get("problems_created")
        if isinstance(problems, list):
            problems_str = " ".join(str(p) for p in problems)[:500] if problems else ""
        else:
            problems_str = str(cat.get("problems_created") or "")[:500]
        db.insert_catalyst(
            d,
            title=cat.get("title") or "News",
            summary=cat.get("summary") or "",
            interests=cat.get("interests") or [],
            problems_created=problems_str or (str(cat.get("problems_created") or "")[:500]),
            source_urls=cat.get("source_urls") or [],
            what_changed=cat.get("what_changed"),
            who_feels_it=cat.get("who_feels_it"),
            opportunity_wedge=cat.get("opportunity_wedge"),
            confidence=cat.get("confidence"),
        )
    catalysts_deduped = _catalyst_dedupe_by_topic(catalysts)

    # 5) Build pain_clusters payload for compose_idea_cards
    pain_clusters_for_cards: list[dict[str, Any]] = []
    for c in clusters_for_cards:
        cid = str(c["id"])
        items = items_by_cluster.get(cid, [])
        evidence_snippets = [s for it in items for s in (it.get("evidence_snippets") or [])][:10]
        links = list(c.get("example_urls") or [])[:5]
        if not links:
            links = [it.get("url") for it in items if it.get("url")][:5]
        pain_clusters_for_cards.append({
            "title": c.get("title") or "",
            "summary": c.get("summary") or "",
            "evidence_snippets": evidence_snippets,
            "example_urls": links,
            "links": links,
        })

    # 6) Compose idea cards (one Gemini call)
    idea_cards = compose_idea_cards(pain_clusters_for_cards, catalysts_deduped)

    # 7) Build markdown from idea cards; "Today's themes:" from top 2–3 idea_title
    lines = [f"# Unmet — {d}", "", get_intro(), "", ""]
    themes_line = get_todays_themes_from_idea_cards(idea_cards, top_n=3)
    if themes_line:
        lines.append(themes_line)
        lines.append("")

    lines.append("## Idea Cards")
    lines.append("")
    bet_candidates: list[tuple[Any, float]] = []
    for i, card in enumerate(idea_cards):
        lines.append(format_idea_card(card))
        # Debug logging: which snippets supported pain/catalyst, which URLs, coherence
        ps = card.get("pain_signal") or {}
        cs = card.get("catalyst_signal") or {}
        pain_snips = ps.get("evidence_snippets") or []
        cat_snips = cs.get("evidence_snippets") or []
        urls = list(ps.get("links") or []) + list(cs.get("links") or [])
        logger.info(
            "published_card idx=%s idea_title=%s pain_snippets=%s catalyst_snippets=%s urls=%s",
            i,
            (card.get("idea_title") or "")[:50],
            pain_snips[:3],
            cat_snips[:3],
            urls[:5],
        )
        wedge = card.get("wedge") or ""
        if wedge and "unclear from evidence" not in wedge.lower():
            bet_candidates.append((card, card.get("confidence", 0.5)))

    lines.append("---")
    lines.append("")
    if bet_candidates:
        best = max(bet_candidates, key=lambda x: x[1])
        lines.append("One line I'd bet on: " + (best[0].get("wedge") or ""))
    else:
        lines.append("Worth exploring: re-run with more data.")
    lines.append("")

    md = "\n".join(lines)
    db.upsert_daily_report(d, md)

    out_dir = Path(__file__).resolve().parent.parent.parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{d}.md"
    out_path.write_text(md, encoding="utf-8")
    logger.info("Report for %s written to %s", d, out_path)
    return md
