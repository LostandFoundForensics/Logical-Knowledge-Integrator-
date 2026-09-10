"""
Android Excavator CLI — plain language.

  android_excavator list
  android_excavator scan /path/to/folder_dump
  android_excavator extract /path/to/folder_dump --out ./case_out
  android_excavator extract /path/to/folder_dump --parsers sms,calls
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from android_excavator.core.engine import list_parsers, run_extract
from android_excavator.core.source import FolderDump
from android_excavator.export.writers import write_jsonl, write_summary_csv


def cmd_list(_args: argparse.Namespace) -> int:
    print("Android Excavator parsers (pick by id):\n")
    for p in list_parsers():
        print(f"  [{p['category']}]")
        print(f"    {p['id']:12}  {p['label']}")
        print(f"    {'':12}  {p['description']}\n")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    dump = FolderDump(args.root)
    n = dump.scan()
    print(f"Root:  {dump.root}")
    print(f"Files: {n}")
    interesting = [
        "mmssms.db", "contacts2.db", "calllog.db", "History",
        "telephony.db", "browser2.db",
    ]
    print("\nKnown artifact files found:")
    found_any = False
    for name in interesting:
        hits = dump.find_by_name(name)
        if hits:
            found_any = True
            for h in hits[:5]:
                print(f"  {name:16}  {dump.logical_path(h)}")
            if len(hits) > 5:
                print(f"  {'':16}  … and {len(hits) - 5} more")
    if not found_any:
        print("  (none of the common names — try extract anyway or check the path)")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    parser_ids = None
    if args.parsers:
        parser_ids = [p.strip() for p in args.parsers.split(",") if p.strip()]
    print(f"Scanning {args.root} …")
    records = run_extract(
        args.root,
        parser_ids=parser_ids,
        limit_per_parser=args.limit,
    )
    counts = Counter(r.artifact_type for r in records)
    print(f"Artifacts: {len(records)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")

    out = Path(args.out or Path(args.root).name + "_excavator_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_jsonl(records, out / "artifacts.jsonl")
    csv_path = write_summary_csv(records, out / "summary.csv")
    meta = {
        "tool": "AndroidExcavator",
        "version": "1.0.0",
        "root": str(Path(args.root).resolve()),
        "artifact_count": len(records),
        "by_type": dict(counts),
        "parsers": parser_ids or [p["id"] for p in list_parsers()],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL  → {jl}")
    print(f"CSV    → {csv_path}")
    print(f"Meta   → {out / 'run_meta.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="android_excavator",
        description="Android Excavator — parse an Android folder dump (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="Show available parsers in plain language")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("scan", help="Look for known databases under a folder dump")
    p.add_argument("root", help="Path to the folder dump root")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("extract", help="Extract artifacts from a folder dump")
    p.add_argument("root", help="Path to the folder dump root")
    p.add_argument("--out", default="", help="Output folder for results")
    p.add_argument(
        "--parsers",
        default="",
        help="Comma-separated parser ids (default: all). Example: sms,calls,chrome",
    )
    p.add_argument("--limit", type=int, default=50_000, help="Max rows per parser")
    p.set_defaults(func=cmd_extract)

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
