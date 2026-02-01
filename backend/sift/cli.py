"""CLI: ingest, analyze, run, seed."""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from .run.render_sample import run_render_sample

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _date(s: str) -> str:
    try:
        date.fromisoformat(s)
        return s
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date: {s!r} (use YYYY-MM-DD)")


def main() -> int:
    parser = argparse.ArgumentParser(prog="sift", description="Sift newsletter pipeline (python -m sift)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest HN, Reddit, RSS for a date")
    p_ingest.add_argument("--date", type=_date, default=str(date.today()), metavar="YYYY-MM-DD", help="Target date")

    p_analyze = sub.add_parser("analyze", help="Pain score, label, cluster for a date")
    p_analyze.add_argument("--date", type=_date, default=str(date.today()), metavar="YYYY-MM-DD", help="Target date")

    p_run = sub.add_parser("run", help="Summarize clusters, catalysts, write report for a date")
    p_run.add_argument("--date", type=_date, default=str(date.today()), metavar="YYYY-MM-DD", help="Target date")

    p_seed = sub.add_parser("seed", help="Seed interests and interest_sources")

    p_render = sub.add_parser("render_sample", help="Output a sample newsletter in the new style (no API)")

    args = parser.parse_args()
    try:
        if args.cmd == "ingest":
            from .ingest import run_ingest
            n = run_ingest(args.date)
            print(f"Ingested {n} items.")
        elif args.cmd == "run":
            from .run.runner import run_report
            run_report(args.date)
            print("Report written to daily_reports and /out/<date>.md")
        elif args.cmd == "analyze":
            from .analyze import run_analyze
            run_analyze(args.date)
            print("Analyze complete.")
        elif args.cmd == "seed":
            from .seed_data import run_seed
            run_seed()
            print("Seed complete.")
        elif args.cmd == "render_sample":
            md = run_render_sample()
            print(md)
        return 0
    except Exception as e:
        logging.exception("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
