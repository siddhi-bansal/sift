#!/usr/bin/env python3
"""Dump clusters, catalysts, and raw item count for a date (for debugging)."""
import json
import sys
from pathlib import Path

# run from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from unmet import db

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "2026-01-31"
    print(f"\n========== DB STATE FOR {date_str} ==========\n")
    clusters = db.get_clusters_for_date(date_str)
    catalysts = db.get_catalysts_for_date(date_str)
    raw = db.raw_items_for_date(date_str)
    report = db.get_daily_report(date_str)
    print(f"Raw items (fetched on this date): {len(raw)}")
    print(f"Clusters: {len(clusters)}")
    for i, c in enumerate(clusters):
        print(f"\n--- Cluster {i+1} (id={c.get('id')}, size={c.get('size')}, score={c.get('score')}) ---")
        print(f"  title: {c.get('title')}")
        print(f"  summary: {c.get('summary', '')[:300]}...")
        print(f"  persona: {c.get('persona')}")
        print(f"  why_matters: {c.get('why_matters', '')[:200]}...")
        print(f"  top_terms: {c.get('top_terms')}")
        print(f"  example_urls: {c.get('example_urls')}")
    print(f"\nCatalysts: {len(catalysts)}")
    for i, cat in enumerate(catalysts):
        print(f"\n--- Catalyst {i+1} ---")
        print(f"  title: {cat.get('title')}")
        print(f"  summary: {cat.get('summary', '')[:200]}...")
        print(f"  interests: {cat.get('interests')}")
        print(f"  problems_created: {cat.get('problems_created', '')[:150]}...")
        print(f"  source_urls: {cat.get('source_urls')}")
    print(f"\nDaily report length: {len(report or '')} chars")
    if report:
        print("\n--- Full report markdown (first 2000 chars) ---")
        print((report or "")[:2000])

if __name__ == "__main__":
    main()
