"""CLI: ingest, analyze, run, seed."""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from . import db
from .analyze import run_analyze
from .ingest import run_ingest
from .run import run_report
from .seed_data import run_seed

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
    parser = argparse.ArgumentParser(prog="unmet", description="Unmet newsletter pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest HN, Reddit, RSS for a date")
    p_ingest.add_argument("--date", type=_date, default=str(date.today()), metavar="YYYY-MM-DD", help="Target date")
    p_ingest.set_defaults(func=lambda a: run_ingest(a.date))

    p_analyze = sub.add_parser("analyze", help="Pain score, label, cluster for a date")
    p_analyze.add_argument("--date", type=_date, default=str(date.today()), metavar="YYYY-MM-DD", help="Target date")
    p_analyze.set_defaults(func=lambda a: run_analyze(a.date))

    p_run = sub.add_parser("run", help="Summarize clusters, catalysts, write report for a date")
    p_run.add_argument("--date", type=_date, default=str(date.today()), metavar="YYYY-MM-DD", help="Target date")
    p_run.set_defaults(func=lambda a: run_report(a.date))

    p_seed = sub.add_parser("seed", help="Seed interests and interest_sources")
    p_seed.set_defaults(func=lambda a: run_seed())

    args = parser.parse_args()
    try:
        fn = args.func
        if args.cmd == "ingest":
            n = fn(args)
            print(f"Ingested {n} items.")
        elif args.cmd == "run":
            fn(args)
            print("Report written to daily_reports and /out/<date>.md")
        elif args.cmd == "analyze":
            fn(args)
            print("Analyze complete.")
        elif args.cmd == "seed":
            fn(args)
            print("Seed complete.")
        return 0
    except Exception as e:
        logging.exception("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
