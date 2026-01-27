"""Run report for a date: summarize clusters, catalyst bullets, build markdown, write daily_reports + /out/YYYY-MM-DD.md."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from .. import db
from ..gemini_client import catalyst_bullets, summarize_cluster

logger = logging.getLogger(__name__)


def _cluster_items_for_date(date_str: str) -> dict[str, list[dict[str, Any]]]:
    """Return cluster_id -> list of raw_items in that cluster."""
    with db.get_conn() as conn:
        cur = conn.cursor()
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
        rows = cur.fetchall()
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        cid = r["cluster_id"]
        if cid not in out:
            out[cid] = []
        out[cid].append({"id": r["id"], "title": r["title"], "text": r["text"], "url": r["url"], "source": r["source"]})
    return out


def run_report(target_date: str | None = None) -> str:
    """
    Run report for target_date: summarize clusters, catalyst bullets, build markdown.
    Writes to daily_reports and /out/YYYY-MM-DD.md. Returns markdown string.
    """
    d = target_date or str(date.today())

    # 1) Summarize each cluster with Gemini
    clusters = db.get_clusters_for_date(d)
    items_by_cluster = _cluster_items_for_date(d)
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
            db.update_cluster(cid, out["title"], out["summary"], out["persona"], out["why_matters"], urls)
        except Exception as e:
            logger.warning("summarize_cluster failed for %s: %s", cid, e)

    # 2) Catalyst bullets from RSS news items (replace previous catalysts for this date)
    db.delete_catalysts_for_date(d)
    all_items = db.raw_items_for_date(d)
    labels = db.get_item_labels_for_raw_ids([str(r["id"]) for r in all_items])
    news_items = [
        {"title": r.get("title"), "url": r.get("url"), "text": (r.get("text") or "")[:800]}
        for r in all_items
        if r.get("source") == "rss" or labels.get(str(r["id"]), {}).get("label") == "NEWS"
    ]
    catalysts = catalyst_bullets(news_items, max_bullets=7)
    for cat in catalysts:
        db.insert_catalyst(
            d,
            title=cat.get("title") or "News",
            summary=cat.get("summary") or "",
            interests=cat.get("interests") or [],
            problems_created=cat.get("problems_created") or "",
            source_urls=cat.get("source_urls") or [],
        )

    # 3) Rising clusters (compare to previous day) — re-fetch clusters after summarization
    prev = db.get_previous_day_clusters(d)
    clusters = db.get_clusters_for_date(d)
    rising: list[dict[str, Any]] = []
    if prev and clusters:
        # Simple overlap on top_terms as "rising"
        prev_terms = set()
        for p in prev[:10]:
            prev_terms.update((p.get("top_terms") or [])[:5])
        for c in clusters:
            terms = set((c.get("top_terms") or [])[:5])
            if terms and terms - prev_terms and len(terms - prev_terms) >= 2:
                rising.append(c)

    # 4) Wildcard: one odd but interesting item (e.g. first OTHER or small cluster)
    wildcard_item: dict[str, Any] | None = None
    for r in all_items:
        lb = labels.get(str(r["id"]), {}).get("label")
        if lb == "OTHER" and (r.get("title") or "").strip():
            wildcard_item = r
            break
    if not wildcard_item and all_items:
        wildcard_item = all_items[0]

    # 5) Build markdown
    lines = [f"# Unmet — {d}", "", "## 1. Top Pain Clusters", ""]
    for c in (clusters or [])[:5]:
        lines.append(f"### {c.get('title') or 'Pain cluster'}")
        lines.append("")
        if c.get("summary"):
            lines.append(c["summary"])
            lines.append("")
        if c.get("persona"):
            lines.append(f"**Who:** {c['persona']}")
        if c.get("why_matters"):
            lines.append(f"**Why it matters:** {c['why_matters']}")
        lines.append("")
        for u in (c.get("example_urls") or [])[:5]:
            if u:
                lines.append(f"- {u}")
        lines.append("")

    lines.append("## 2. Rising Pain Signals")
    lines.append("")
    if rising:
        for c in rising[:5]:
            lines.append(f"- **{c.get('title') or 'Rising'}** — { (c.get('summary') or '')[:200]}...")
        lines.append("")
    else:
        lines.append("*(No strong delta vs yesterday.)*")
        lines.append("")

    lines.append("## 3. Catalyst Signals")
    lines.append("")
    cats = db.get_catalysts_for_date(d)
    for cat in (cats or [])[:7]:
        lines.append(f"### {cat.get('title') or 'News'}")
        lines.append(cat.get("summary") or "")
        if cat.get("problems_created"):
            lines.append(f"**Problems / urgency:** {cat['problems_created']}")
        for u in (cat.get("source_urls") or [])[:3]:
            if u:
                lines.append(f"- {u}")
        lines.append("")

    lines.append("## 4. Wildcard")
    lines.append("")
    if wildcard_item:
        lines.append(f"**{wildcard_item.get('title') or 'Item'}**")
        text = (wildcard_item.get("text") or "")[:300]
        if text:
            lines.append(text + ("..." if len((wildcard_item.get("text") or "")) > 300 else ""))
        if wildcard_item.get("url"):
            lines.append(f"\n{wildcard_item['url']}")
    else:
        lines.append("*(None this time.)*")
    lines.append("")

    md = "\n".join(lines)
    db.upsert_daily_report(d, md)

    # 6) Write /out/YYYY-MM-DD.md
    out_dir = Path(__file__).resolve().parent.parent.parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{d}.md"
    out_path.write_text(md, encoding="utf-8")
    logger.info("Report for %s written to %s", d, out_path)
    return md


# Fix: _cluster_items_for_date uses db.get_conn but we're inside the run package; get_conn is in db module. We already import db, so db.get_conn is correct. But get_conn is a context manager that yields conn - we're using it with "with db.get_conn() as conn" - we need to make sure we're calling it correctly. We have "with db.get_conn() as conn" - but get_conn is from unittest.db. Let me check - we have "from .. import db" so db.get_conn works. But in _cluster_items_for_date we're not in a with-block for get_conn - we're calling get_conn and then using conn. So we need "with db.get_conn() as conn: ...". I wrote "with db.get_conn() as conn:" and then cur = conn.cursor() etc. So we're good. But wait - we're calling get_conn from db - and the run/runner imports db. So we need to use the same pattern as in db.py. We have "with get_conn() as conn" in db.py. So from run/runner we do "with db.get_conn() as conn:". But get_conn is not exported from db by default - we need to check. Looking at db.py we define get_conn at module level. So db.get_conn exists. Good.

One bug: in _cluster_items_for_date I'm using db.get_conn - but that's the module we imported. So we need to actually use it. I wrote "with db.get_conn() as conn:" - we need to add that. Let me look at my _cluster_items_for_date again. I wrote:
  with db.get_conn() as conn:
    cur = conn.cursor()
    ...
  rows = cur.fetchall()
So rows is inside the with block - we need rows = cur.fetchall() before exiting. So the structure is:
  with db.get_conn() as conn:
    cur = conn.cursor()
    cur.execute(...)
    rows = cur.fetchall()
  out = {}
  for r in rows: ...
That's correct. Good.

Remove the stray "from .. import db as db_module" in run_report.
</think>

<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
StrReplace