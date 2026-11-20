"""Command line for the drill tracker."""
from __future__ import annotations

import argparse

from .drills import DrillError, load, overdue, parse_date, summarize, trend


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(prog="drilltrack", description="Evacuation drill tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("summary", help="timing statistics per building")
    p.add_argument("file")
    p.add_argument("--target", type=int, default=300, help="target evacuation time in seconds (default 300)")
    p = sub.add_parser("trend", help="drills of one building with change since the last drill")
    p.add_argument("file")
    p.add_argument("--building", required=True)
    p = sub.add_parser("overdue", help="buildings with no recent drill")
    p.add_argument("file")
    p.add_argument("--today", required=True, help="YYYY-MM-DD")
    p.add_argument("--interval-days", type=int, default=180)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line. Exit 1 when `overdue` finds buildings, 2 on bad input."""
    args = build_parser().parse_args(argv)
    try:
        drills = load(args.file)
        if args.command == "summary":
            print(f"{'Building':<12} {'Drills':>6} {'Mean':>7} {'Median':>7} {'Best':>5} {'Worst':>6}  Within {args.target}s")
            for s in summarize(drills, args.target):
                print(f"{s.building:<12} {s.count:>6} {s.mean:>7.0f} {s.median:>7.0f} {s.best:>5} "
                      f"{s.worst:>6}  {s.within_target} of {s.count}")
            return 0
        if args.command == "trend":
            for d, change in trend(drills, args.building):
                delta = "first" if change is None else f"{change:+d}s"
                note = f"  {d.issues}" if d.issues else ""
                print(f"{d.day}  {d.drill_type:<10} {d.seconds:>4}s  {delta:>6}{note}")
            return 0
        rows = overdue(drills, parse_date(args.today), args.interval_days)
        for building, last, days in rows:
            print(f"{building:<12} last drill {last}  ({days} days ago)")
        print(f"{len(rows)} building(s) overdue" if rows else "No building is overdue")
        return 1 if rows else 0
    except DrillError as exc:
        print(f"error: {exc}")
        return 2
