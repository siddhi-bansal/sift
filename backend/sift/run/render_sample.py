"""Render a sample newsletter from fixtures using the new style (no Gemini)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..newsletter_style import (
    build_one_line_bet,
    buildability_score_catalyst,
    buildability_score_pain,
    evidence_from_catalyst,
    evidence_from_cluster_items,
    format_item,
    get_intro,
    get_pattern_language,
    has_urgency_keywords,
    impact_from_catalyst,
    rewrite_into_template,
    signal_strength_from_cluster,
)


def _fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures" / "sample_newsletter_data.json"


def run_render_sample(fixture_path: Path | None = None) -> str:
    """
    Load fixture data, build newsletter in the new style using deterministic fallback (no Gemini).
    Returns the full markdown string.
    """
    path = fixture_path or _fixture_path()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    d = data.get("date", "2026-01-27")
    clusters = data.get("clusters", [])
    catalysts = data.get("catalysts", [])
    wildcard = data.get("wildcard")

    bet_candidates: list[tuple[Any, float]] = []
    lines = [f"# Sift — {d}", "", get_intro(), "", ""]

    cluster_titles = [c.get("title") or "" for c in clusters[:5]]
    catalyst_titles = [cat.get("title") or "" for cat in catalysts[:5]]
    pattern = get_pattern_language(cluster_titles, catalyst_titles)
    if pattern:
        lines.append(pattern)
        lines.append("")

    lines.append("## 1. Top Pain Clusters")
    lines.append("")
    for c in clusters[:5]:
        items = c.get("items") or []
        evidence = evidence_from_cluster_items(items, max_snippets=3, max_links=3)
        if not evidence.links and not evidence.snippets:
            continue
        size = len(items)
        score = float(c.get("score") or 0.5)
        avg_conf = 0.6
        strength = signal_strength_from_cluster(size, score, avg_conf)
        draft = {
            "title": c.get("title") or "",
            "summary": c.get("summary") or "",
            "persona": c.get("persona") or "",
            "why_matters": c.get("why_matters") or "",
        }
        item = rewrite_into_template(draft, "pain_cluster", evidence, strength, use_gemini=False)
        bet_candidates.append((item, buildability_score_pain(item.strength_or_impact, item.who, item.wedge)))
        lines.append(format_item(item, "pain_cluster"))

    lines.append("## 2. Rising Pain Signals")
    lines.append("")
    lines.append("No clear risers today.")
    lines.append("")

    lines.append("## 3. Catalyst Signals")
    lines.append("")
    for cat in catalysts[:5]:
        evidence = evidence_from_catalyst(cat)
        if not evidence.links and not evidence.snippets:
            continue
        interests = cat.get("interests") or []
        urls = cat.get("source_urls") or []
        summary_and_problems = (cat.get("summary") or "") + " " + (cat.get("problems_created") or "")
        impact = impact_from_catalyst(
            len(interests),
            len(urls),
            has_urgency_keywords(summary_and_problems),
        )
        draft = {
            "title": cat.get("title") or "",
            "summary": cat.get("summary") or "",
            "persona": "",
            "why_matters": cat.get("problems_created") or "",
        }
        item = rewrite_into_template(draft, "catalyst", evidence, impact, use_gemini=False)
        bet_candidates.append((item, buildability_score_catalyst(item.strength_or_impact, cat.get("problems_created") or "")))
        lines.append(format_item(item, "catalyst"))

    lines.append("## 4. Wildcard")
    lines.append("")
    if wildcard:
        evidence = evidence_from_cluster_items([wildcard], max_snippets=3, max_links=3)
        draft = {
            "title": wildcard.get("title") or "Item",
            "summary": (wildcard.get("text") or "")[:200],
            "persona": "",
            "why_matters": "",
        }
        item = rewrite_into_template(draft, "wildcard", evidence, "Med", use_gemini=False)
        bet_candidates.append((item, buildability_score_pain("Med", item.who, item.wedge)))
        lines.append(format_item(item, "pain_cluster"))
    else:
        lines.append("*(None this time.)*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(build_one_line_bet(bet_candidates))
    lines.append("")

    return "\n".join(lines)
