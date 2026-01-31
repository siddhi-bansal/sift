"""Run report for a date: summarize clusters, coherence gate, idea cards, build markdown, write daily_reports + /out/YYYY-MM-DD.md."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from .. import db
from ..analyze.topic_coherence import validate_topic_coherence
from ..gemini_client import (
    catalyst_bullets,
    compose_startup_grade_cards,
    generate_one_bet,
    rename_to_failure_mode,
    rename_to_match_evidence,
    startup_grade_editor_gate,
    summarize_cluster,
)
from ..newsletter_style import (
    format_startup_grade_card,
    get_intro,
    get_todays_themes_from_startup_cards,
    repair_startup_grade_card,
    validate_startup_grade_card_split,
)

logger = logging.getLogger(__name__)


def _cluster_items_for_date(date_str: str) -> dict[str, list[dict[str, Any]]]:
    """Return cluster_id -> list of raw_items in that cluster. Includes metadata and source_id for evidence links."""
    with db.get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT c.id::text AS cluster_id, r.id, r.source_id, r.title, r.text, r.url, r.source, r.evidence_snippets, r.metadata
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
                    SELECT c.id::text AS cluster_id, r.id, r.source_id, r.title, r.text, r.url, r.source, r.metadata
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
        row = {
            "id": r["id"],
            "source_id": r.get("source_id"),
            "title": r["title"],
            "text": r["text"],
            "url": r["url"],
            "source": r["source"],
            "metadata": r.get("metadata") or {},
        }
        if r.get("evidence_snippets") is not None:
            row["evidence_snippets"] = list(r["evidence_snippets"]) if r["evidence_snippets"] else []
        else:
            row["evidence_snippets"] = []
        out[cid].append(row)
    return out


def _build_evidence_bullets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build structured evidence bullets from cluster items: quote, post_id, post_url, comment_id, comment_url.
    HN items: use source_id as post_id, url as post_url; match evidence_snippets to metadata.comments for comment links.
    """
    bullets: list[dict[str, Any]] = []
    for it in items[:15]:
        post_id = it.get("source_id") or ""
        post_url = it.get("url") or (f"https://news.ycombinator.com/item?id={post_id}" if post_id else "")
        if it.get("source") != "hn" or not post_id:
            # Non-HN: post-level only
            for s in (it.get("evidence_snippets") or [])[:3]:
                if (s or "").strip():
                    bullets.append({
                        "quote": (s or "").strip()[:200],
                        "post_id": post_id,
                        "post_url": post_url,
                        "comment_id": None,
                        "comment_url": None,
                    })
            continue
        comments = (it.get("metadata") or {}).get("comments") or []
        snippet_to_comment: dict[str, dict] = {}
        for c in comments:
            ct = (c.get("text") or "").strip()
            if not ct:
                continue
            for s in (it.get("evidence_snippets") or []):
                s = (s or "").strip()
                if not s or len(s.split()) > 12:
                    continue
                if s in ct or (len(s) >= 8 and s.lower() in ct.lower()):
                    snippet_to_comment[s] = c
                    break
        for s in (it.get("evidence_snippets") or [])[:5]:
            s = (s or "").strip()
            if not s:
                continue
            c = snippet_to_comment.get(s)
            if c:
                bullets.append({
                    "quote": s[:200],
                    "post_id": post_id,
                    "post_url": c.get("post_url") or post_url,
                    "comment_id": c.get("comment_id"),
                    "comment_url": c.get("comment_url"),
                })
            else:
                bullets.append({
                    "quote": s[:200],
                    "post_id": post_id,
                    "post_url": post_url,
                    "comment_id": None,
                    "comment_url": None,
                })
    return bullets[:15]


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

    # 5) Build pain_clusters payload with topic_tags for Startup-Grade Editor Gate
    pain_clusters_for_cards: list[dict[str, Any]] = []
    for c in clusters_for_cards:
        cid = str(c["id"])
        items = items_by_cluster.get(cid, [])
        evidence_snippets = [s for it in items for s in (it.get("evidence_snippets") or [])][:10]
        evidence_bullets = _build_evidence_bullets(items)
        links = list(c.get("example_urls") or [])[:5]
        if not links:
            links = [it.get("url") for it in items if it.get("url")][:5]
        topic_tags: list[str] = []
        for it in items:
            topic_tags.extend(labels.get(str(it["id"]), {}).get("topic_tags") or [])
        pain_clusters_for_cards.append({
            "title": c.get("title") or "",
            "summary": c.get("summary") or "",
            "evidence_snippets": evidence_snippets,
            "evidence_bullets": evidence_bullets,
            "example_urls": links,
            "links": links,
            "topic_tags": list(dict.fromkeys(topic_tags))[:10],
        })

    # 5b) Startup-Grade Editor Gate: select items that pass buildability; log rejects
    gate_result = startup_grade_editor_gate(pain_clusters_for_cards, catalysts_deduped)
    selected_pain_idx = gate_result.get("selected_pain_indices") or []
    selected_cat_idx = gate_result.get("selected_catalyst_indices") or []
    rejects = gate_result.get("rejects") or []
    for r in rejects:
        logger.info("buildability_gate_reject kind=%s index=%s reason=%s", r.get("kind"), r.get("index"), r.get("reason"))

    selected_pain_clusters = [pain_clusters_for_cards[i] for i in selected_pain_idx if 0 <= i < len(pain_clusters_for_cards)]
    selected_catalysts = [catalysts_deduped[i] for i in selected_cat_idx if 0 <= i < len(catalysts_deduped)]

    # 5c) Failure-mode titles for selected pain clusters
    for cluster in selected_pain_clusters:
        title = cluster.get("title") or ""
        snippets = cluster.get("evidence_snippets") or []
        if title and snippets:
            new_title = rename_to_failure_mode(title, snippets)
            if new_title and new_title != title:
                logger.info("failure_mode_rename old=%s new=%s", title[:50], new_title[:50])
                cluster["title"] = new_title

    # 6) Compose Startup-Grade Idea Cards (one Gemini call)
    raw_cards = compose_startup_grade_cards(selected_pain_clusters, selected_catalysts)

    # Build allowed URLs from clusters (anti-hallucination: never invent links)
    allowed_urls: set[str] = set()
    cluster_links_list: list[str] = []
    for c in selected_pain_clusters:
        for u in (c.get("example_urls") or c.get("links") or [])[:10]:
            if u and isinstance(u, str):
                allowed_urls.add(u.strip())
                cluster_links_list.append(u.strip())
        for b in (c.get("evidence_bullets") or [])[:20]:
            if isinstance(b, dict):
                for key in ("post_url", "comment_url"):
                    u = b.get(key)
                    if u and isinstance(u, str) and u.strip():
                        allowed_urls.add(u.strip())
                        cluster_links_list.append(u.strip())
    cluster_links = list(dict.fromkeys(cluster_links_list))[:10]

    # 6b) Validate split (HARD_FAIL = drop, SOFT_FAIL = repair then re-validate)
    idea_cards: list[dict[str, Any]] = []
    validation_rejects: list[dict[str, Any]] = []
    for i, card in enumerate(raw_cards):
        hard, soft, warnings = validate_startup_grade_card_split(card, allowed_urls=allowed_urls)
        if hard:
            validation_rejects.append({"title": card.get("title") or "", "errors": hard + soft})
            logger.info("buildability_hard_fail card idx=%s title=%s hard=%s", i, (card.get("title") or "")[:50], hard)
            continue
        if soft or warnings:
            repaired = repair_startup_grade_card(card, cluster_links=cluster_links)
            hard2, soft2, warnings2 = validate_startup_grade_card_split(repaired, allowed_urls=allowed_urls)
            if hard2:
                validation_rejects.append({"title": repaired.get("title") or "", "errors": hard2 + soft2})
                logger.info("buildability_hard_fail_after_repair card idx=%s title=%s", i, (repaired.get("title") or "")[:50])
                continue
            repaired["_warnings"] = list(warnings) + list(warnings2) + list(soft2)
            idea_cards.append(repaired)
            logger.info("buildability_pass_after_repair card idx=%s title=%s warnings=%s", i, (repaired.get("title") or "")[:50], repaired.get("_warnings"))
        else:
            idea_cards.append(card)
            logger.info("buildability_pass card idx=%s title=%s", i, (card.get("title") or "")[:50])

    # 7) Report: Header, themes, cards (or Draft section if <2 cards), One bet, Rejects
    lines = [f"# Unmet — {d}", "", get_intro(), "", ""]
    themes_line = get_todays_themes_from_startup_cards(idea_cards, top_n=3)
    if themes_line:
        lines.append(themes_line)
        lines.append("")

    use_draft_section = len(idea_cards) < 2
    if use_draft_section:
        lines.append("## Draft / Needs more receipts")
        lines.append("")
        for i, card in enumerate(idea_cards):
            w = card.get("_warnings") or []
            lines.append(format_startup_grade_card(card, warnings=w, is_draft=True))
            logger.info("draft_card idx=%s title=%s", i, (card.get("title") or "")[:50])
    else:
        lines.append("## Startup-Grade Idea Cards")
        lines.append("")
        for i, card in enumerate(idea_cards):
            w = card.get("_warnings") or []
            lines.append(format_startup_grade_card(card, warnings=w, is_draft=False))
            logger.info(
                "published_card idx=%s title=%s who_pays=%s mvp=%s",
                i,
                (card.get("title") or "")[:50],
                (card.get("who_pays") or "")[:40],
                ((card.get("wedge") or {}).get("mvp") or "")[:40],
            )

    lines.append("---")
    lines.append("")
    one_bet = generate_one_bet(idea_cards)
    lines.append("One bet: " + one_bet)
    lines.append("")

    # Rejects (editor gate + validation drops) for transparency
    if rejects or validation_rejects:
        lines.append("---")
        lines.append("")
        lines.append("## Rejects (buildability gate)")
        lines.append("")
        for r in rejects:
            lines.append(f"- **{r.get('kind', '')}** index {r.get('index', '')}: {r.get('reason', '')}")
        for vr in validation_rejects:
            lines.append(f"- **Card dropped** \"{vr.get('title', '')[:60]}\": {', '.join(vr.get('errors', []))}")
        lines.append("")

    md = "\n".join(lines)
    db.upsert_daily_report(d, md)

    out_dir = Path(__file__).resolve().parent.parent.parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{d}.md"
    out_path.write_text(md, encoding="utf-8")
    logger.info("Report for %s written to %s", d, out_path)
    return md
