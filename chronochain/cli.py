"""
ChronoChain CLI — simple timeline builder.

  chronochain init ./case_timeline
  chronochain add-sms ./case_timeline /path/to/mmssms.db
  chronochain correlate ./case_timeline
  chronochain export ./case_timeline --csv timeline.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chronochain.store import TimelineStore
from chronochain.correlation import build_links, CorrelationConfig
from chronochain.ingest.sms_calls import ingest_android_sms
from chronochain.export import export_csv, export_jsonl


def _db_path(case_dir: str) -> Path:
    p = Path(case_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / "timeline.db"


def cmd_init(args: argparse.Namespace) -> int:
    db = _db_path(args.case_dir)
    store = TimelineStore(str(db))
    store.close()
    print(f"Timeline ready: {db}")
    return 0


def cmd_add_sms(args: argparse.Namespace) -> int:
    db = _db_path(args.case_dir)
    store = TimelineStore(str(db))
    events = ingest_android_sms(
        Path(args.sms_db),
        evidence_id=args.evidence_id or Path(args.sms_db).name,
        limit=args.limit,
    )
    n = store.upsert_many(events)
    store.close()
    print(f"Added {n} SMS event(s) from {args.sms_db}")
    print(f"Total events in timeline: {TimelineStore(str(db)).count()}")
    return 0


def cmd_correlate(args: argparse.Namespace) -> int:
    db = _db_path(args.case_dir)
    store = TimelineStore(str(db))
    events = store.list_events(limit=args.limit)
    links, _ = build_links(events, CorrelationConfig())
    n = store.save_links(links)
    store.close()
    print(f"Stored {n} proximity link(s) for {len(events)} event(s)")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    db = _db_path(args.case_dir)
    store = TimelineStore(str(db))
    events = store.list_events(limit=args.limit, category=args.category or None)
    store.close()
    out_dir = Path(args.case_dir)
    if args.jsonl:
        p = export_jsonl(events, out_dir / args.jsonl)
        print(f"JSONL → {p} ({len(events)} events)")
    if args.csv:
        p = export_csv(events, out_dir / args.csv)
        print(f"CSV   → {p} ({len(events)} events)")
    if not args.jsonl and not args.csv:
        p = export_csv(events, out_dir / "timeline.csv")
        print(f"CSV   → {p} ({len(events)} events)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    db = _db_path(args.case_dir)
    if not db.exists():
        print(f"No timeline at {db}. Run: chronochain init {args.case_dir}")
        return 1
    store = TimelineStore(str(db))
    print(f"Timeline: {db}")
    print(f"Events:   {store.count()}")
    store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chronochain",
        description="ChronoChain — build a simple forensic timeline (read-only on evidence).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="Create an empty timeline case folder")
    p.add_argument("case_dir")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add-sms", help="Add SMS events from an Android SMS database (read-only)")
    p.add_argument("case_dir")
    p.add_argument("sms_db")
    p.add_argument("--evidence-id", default="")
    p.add_argument("--limit", type=int, default=50_000)
    p.set_defaults(func=cmd_add_sms)

    p = sub.add_parser("correlate", help="Link events that happened close together in time")
    p.add_argument("case_dir")
    p.add_argument("--limit", type=int, default=50_000)
    p.set_defaults(func=cmd_correlate)

    p = sub.add_parser("export", help="Export timeline as CSV and/or JSONL")
    p.add_argument("case_dir")
    p.add_argument("--csv", default="")
    p.add_argument("--jsonl", default="")
    p.add_argument("--category", default="")
    p.add_argument("--limit", type=int, default=100_000)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("status", help="Show how many events are in the timeline")
    p.add_argument("case_dir")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
