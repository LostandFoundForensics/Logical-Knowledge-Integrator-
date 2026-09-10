"""
Recall Engine CLI.

  recall_engine list
  recall_engine scan /path/to/ios_backup --out ./re_out
  recall_engine scan /path --parsers notes,safari,calendar
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from recall_engine.core.engine import list_parsers, scan_backup
from recall_engine.export.writers import write_jsonl, write_summary_csv


def cmd_list(_args: argparse.Namespace) -> int:
    print("Recall Engine parsers:\n")
    for p in list_parsers():
        print(f"  {p['id']:12}  {p['label']}")
        print(f"  {'':12}  {p['description']}\n")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    ids = None
    if args.parsers:
        ids = [x.strip() for x in args.parsers.split(",") if x.strip()]
    print(f"Scanning iOS backup {args.backup} (read-only) …")
    hits = scan_backup(args.backup, parser_ids=ids, limit_per_parser=args.limit)
    counts = Counter(h.artifact_type for h in hits)
    print(f"Artifacts: {len(hits)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    out = Path(args.out or "recall_engine_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_jsonl(hits, out / "artifacts.jsonl")
    csv_path = write_summary_csv(hits, out / "summary.csv")
    meta = {
        "tool": "RecallEngine",
        "version": "1.0.0",
        "backup": str(Path(args.backup).resolve()),
        "count": len(hits),
        "by_type": dict(counts),
        "parsers": ids or [p["id"] for p in list_parsers()],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL → {jl}")
    print(f"CSV   → {csv_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recall_engine",
        description="Recall Engine — iOS artifact depth from backups (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("scan")
    p.add_argument("backup", help="iOS backup folder with Manifest.db")
    p.add_argument("--out", default="")
    p.add_argument("--parsers", default="")
    p.add_argument("--limit", type=int, default=20_000)
    p.set_defaults(func=cmd_scan)
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
