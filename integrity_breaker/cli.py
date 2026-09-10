"""
Integrity Breaker CLI.

  integrity_breaker rules
  integrity_breaker scan /path/to/dump --out ./ib_out
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from integrity_breaker.core.engine import list_rules, scan_path
from integrity_breaker.export.writers import write_jsonl, write_summary_csv


def cmd_rules(_args: argparse.Namespace) -> int:
    print("Built-in indicator rules (not automatic guilt):\n")
    for r in list_rules():
        print(f"  [{r['severity']:6}] {r['id']}")
        print(f"           {r['title']}")
        print(f"           {r['description']}\n")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    ids = None
    if args.rules:
        ids = [x.strip() for x in args.rules.split(",") if x.strip()]
    print(f"Scanning {args.path} (read-only) …")
    findings = scan_path(
        args.path,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        rule_ids=ids,
    )
    by_sev = Counter(f.severity for f in findings)
    print(f"Findings: {len(findings)}")
    for k, v in sorted(by_sev.items()):
        print(f"  {k}: {v}")
    out = Path(args.out or "integrity_breaker_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_jsonl(findings, out / "findings.jsonl")
    csv_path = write_summary_csv(findings, out / "findings.csv")
    meta = {
        "tool": "IntegrityBreaker",
        "version": "1.0.0",
        "path": str(Path(args.path).resolve()),
        "finding_count": len(findings),
        "by_severity": dict(by_sev),
        "notes": [
            "Indicators only — not proof of compromise.",
            "Evidence was not modified.",
        ],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL → {jl}")
    print(f"CSV   → {csv_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="integrity_breaker",
        description="Integrity Breaker — IOC/indicator scan over dumps (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("rules")
    p.set_defaults(func=cmd_rules)
    p = sub.add_parser("scan")
    p.add_argument("path")
    p.add_argument("--out", default="")
    p.add_argument("--rules", default="", help="Comma-separated rule ids")
    p.add_argument("--max-files", type=int, default=20_000)
    p.add_argument("--max-file-bytes", type=int, default=1_500_000)
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
