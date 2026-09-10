"""
Bardo Engine CLI.

  bardo sources
  bardo init --case CASE-001 --db ./case.sqlite
  bardo ingest --db ./case.sqlite --from-dir ./my_case/out
  bardo status --db ./case.sqlite
  bardo timeline --db ./case.sqlite --out ./timeline.json
  bardo entities --db ./case.sqlite
  bardo export --db ./case.sqlite --out ./bardo_export
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bardo.core.engine import list_sources, run_ingest
from bardo.core.store import CaseStore
from bardo.export.writers import export_timeline_json, export_summary_json


def cmd_sources(_args: argparse.Namespace) -> int:
    print("Bardo can ingest:\n")
    for s in list_sources():
        print(f"  {s['id']:20}  {s['label']}")
        print(f"  {'':20}  {s['description']}\n")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    store = CaseStore(args.db)
    store.set_meta("case_id", args.case)
    store.set_meta("initialized", "1")
    s = store.summary()
    store.close()
    print(f"Case ready: {args.case}")
    print(f"Store:      {s['path']}")
    print("Observations start at 0 — use `bardo ingest` next.")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    has_any = any([
        args.excavator, args.idriller, args.memory_snare, args.recall,
        args.pattern, args.integrity, args.nimbus, args.truthrelic,
        args.generic, args.from_dir,
    ])
    if not has_any:
        print(
            "Provide --from-dir and/or tool exports "
            "(--excavator, --memory-snare, --idriller, --recall, "
            "--pattern, --integrity, --nimbus, --truthrelic, --generic)",
            file=sys.stderr,
        )
        return 2
    summary = run_ingest(
        args.db,
        excavator_jsonl=args.excavator or None,
        idriller_jsonl=args.idriller or None,
        memory_snare_jsonl=args.memory_snare or None,
        recall_jsonl=args.recall or None,
        pattern_jsonl=args.pattern or None,
        integrity_jsonl=args.integrity or None,
        nimbus_jsonl=args.nimbus or None,
        truthrelic_jsonl=args.truthrelic or None,
        generic_jsonl=args.generic or None,
        from_dir=args.from_dir or None,
        case_id=args.case or "",
    )
    print(f"Observations: {summary.get('observations')}")
    print(f"Entities:     {summary.get('entities')}")
    print(f"By tool:      {summary.get('by_tool')}")
    print(f"By type:      {summary.get('by_type')}")
    if summary.get("dir_stats"):
        nfiles = len(summary["dir_stats"].get("files") or [])
        print(f"From dir:     {summary['dir_stats'].get('total_added')} rows in {nfiles} files")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = CaseStore(args.db)
    s = store.summary()
    store.close()
    print(json.dumps(s, indent=2))
    return 0


def cmd_timeline(args: argparse.Namespace) -> int:
    store = CaseStore(args.db)
    out = Path(args.out or "bardo_timeline.json")
    export_timeline_json(store, out, limit=args.limit)
    n = len(store.timeline(limit=args.limit))
    store.close()
    print(f"Timeline events: {n}")
    print(f"Wrote: {out}")
    return 0


def cmd_entities(args: argparse.Namespace) -> int:
    store = CaseStore(args.db)
    ents = store.list_entities(limit=args.limit)
    store.close()
    for e in ents:
        if isinstance(e, dict):
            print(f"  {e.get('value')}  (count={e.get('obs_count')}, kind={e.get('kind')})")
        else:
            print(f"  {e}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = CaseStore(args.db)
    out = Path(args.out or "bardo_export")
    out.mkdir(parents=True, exist_ok=True)
    t = export_timeline_json(store, out / "timeline.json")
    s = export_summary_json(store, out / "summary.json")
    store.close()
    print(f"Timeline → {t}")
    print(f"Summary  → {s}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bardo",
        description="Bardo Engine — case store and correlation for LoKi tool outputs.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sources", help="List ingest sources")
    p.set_defaults(func=cmd_sources)

    p = sub.add_parser("init", help="Create / open a case database")
    p.add_argument("--case", required=True, help="Case ID")
    p.add_argument("--db", default="./bardo_case.sqlite")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("ingest", help="Load tool exports into the case")
    p.add_argument("--db", default="./bardo_case.sqlite")
    p.add_argument("--case", default="")
    p.add_argument("--from-dir", default="", help="Auto-scan loki case out/ folder")
    p.add_argument("--excavator", default="", help="Android Excavator artifacts.jsonl")
    p.add_argument("--memory-snare", default="", help="Memory Snare artifacts.jsonl")
    p.add_argument("--idriller", default="", help="iDriller artifacts.jsonl")
    p.add_argument("--recall", default="", help="Recall Engine artifacts.jsonl")
    p.add_argument("--pattern", default="", help="Pattern Harvester findings.jsonl")
    p.add_argument("--integrity", default="", help="Integrity Breaker findings.jsonl")
    p.add_argument("--nimbus", default="", help="Nimbus Bridge artifacts.jsonl")
    p.add_argument("--truthrelic", default="", help="Truth Relic inventory.jsonl")
    p.add_argument("--generic", default="", help="Generic JSONL")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("status", help="Show case counts")
    p.add_argument("--db", default="./bardo_case.sqlite")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("timeline", help="Export ordered events with timestamps")
    p.add_argument("--db", default="./bardo_case.sqlite")
    p.add_argument("--out", default="bardo_timeline.json")
    p.add_argument("--limit", type=int, default=10000)
    p.set_defaults(func=cmd_timeline)

    p = sub.add_parser("entities", help="List phones / emails seen in observations")
    p.add_argument("--db", default="./bardo_case.sqlite")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_entities)

    p = sub.add_parser("export", help="Write timeline + summary JSON bundle")
    p.add_argument("--db", default="./bardo_case.sqlite")
    p.add_argument("--out", default="bardo_export")
    p.set_defaults(func=cmd_export)

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
