"""
Memory Snare CLI.

  memory_snare list
  memory_snare scan /path/to/android_dump --out ./ms_out
  memory_snare scan /path --parsers accounts,browser,wifi
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from memory_snare.core.engine import list_parsers, scan_dump
from memory_snare.export.writers import write_jsonl, write_summary_csv


def cmd_list(_args: argparse.Namespace) -> int:
    print("Memory Snare parsers:\n")
    for p in list_parsers():
        print(f"  {p['id']:12}  {p['label']}")
        print(f"  {'':12}  {p['description']}\n")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    ids = None
    if args.parsers:
        ids = [x.strip() for x in args.parsers.split(",") if x.strip()]
    print(f"Scanning {args.path} (read-only) …")
    hits = scan_dump(args.path, parser_ids=ids, limit_per_parser=args.limit)
    counts = Counter(h.artifact_type for h in hits)
    print(f"Artifacts: {len(hits)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    out = Path(args.out or "memory_snare_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_jsonl(hits, out / "artifacts.jsonl")
    csv_path = write_summary_csv(hits, out / "summary.csv")
    meta = {
        "tool": "MemorySnare",
        "version": "1.0.0",
        "path": str(Path(args.path).resolve()),
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
        prog="memory_snare",
        description="Memory Snare — Android artifact parse from folder dumps (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="List parsers")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("scan", help="Scan an Android folder dump")
    p.add_argument("path")
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
