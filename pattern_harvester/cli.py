"""
Pattern Harvester CLI.

  pattern_harvester list
  pattern_harvester scan /path/to/file_or_folder --out ./ph_out
  pattern_harvester scan /path --scanners email,phone,url
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pattern_harvester.core.engine import list_scanners, scan_path
from pattern_harvester.export.writers import write_jsonl, write_summary_csv, counts_by_type


def cmd_list(_args: argparse.Namespace) -> int:
    print("Pattern Harvester scanners:\n")
    for s in list_scanners():
        print(f"  {s['id']:10}  {s['label']}")
        print(f"  {'':10}  {s['description']}\n")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    ids = None
    if args.scanners:
        ids = [x.strip() for x in args.scanners.split(",") if x.strip()]
    print(f"Scanning {args.path} (read-only) …")
    findings = scan_path(
        args.path,
        scanner_ids=ids,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        max_findings=args.max_findings,
    )
    counts = counts_by_type(findings)
    print(f"Findings: {len(findings)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")

    out = Path(args.out or "pattern_harvester_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_jsonl(findings, out / "findings.jsonl")
    csv_path = write_summary_csv(findings, out / "findings.csv")
    meta = {
        "tool": "PatternHarvester",
        "version": "1.0.0",
        "path": str(Path(args.path).resolve()),
        "finding_count": len(findings),
        "by_type": counts,
        "scanners": ids or [s["id"] for s in list_scanners()],
        "notes": [
            "Evidence opened read-only.",
            "Matches are pattern hits, not verified identities.",
        ],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL → {jl}")
    print(f"CSV   → {csv_path}")
    print(f"Meta  → {out / 'run_meta.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pattern_harvester",
        description="Pattern Harvester — find emails, phones, URLs, IPs in files (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="Show scanners")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("scan", help="Scan a file or folder")
    p.add_argument("path", help="File or directory to scan")
    p.add_argument("--out", default="")
    p.add_argument("--scanners", default="", help="Comma list: email,phone,url,ip")
    p.add_argument("--max-files", type=int, default=10_000)
    p.add_argument("--max-file-bytes", type=int, default=32 * 1024 * 1024)
    p.add_argument("--max-findings", type=int, default=100_000)
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
