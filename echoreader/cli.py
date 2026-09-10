"""
EchoReader CLI.

  echoreader checks
  echoreader inspect /path/to/ios_backup
  echoreader inspect /path/to/backup.ab --out ./er_out
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from echoreader.core.engine import inspect_path, list_checks
from echoreader.export.writers import write_report_json


def cmd_checks(_args: argparse.Namespace) -> int:
    print("EchoReader can inspect:\n")
    for c in list_checks():
        print(f"  {c['id']:14}  {c['label']}")
        print(f"  {'':14}  {c['description']}\n")
    print("Decrypt is never the default action.")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    report = inspect_path(args.path)
    print(f"Kind:      {report.kind}")
    print(f"Encrypted: {report.encrypted}")
    print(f"Summary:   {report.summary}")
    if report.findings:
        print("Findings:")
        for f in report.findings:
            print(f"  - {f}")
    if report.warnings:
        print("Warnings:")
        for w in report.warnings:
            print(f"  - {w}")
    if report.next_steps:
        print("Suggested next steps:")
        for s in report.next_steps:
            print(f"  - {s}")
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        p = write_report_json(report, out / "intake_report.json")
        print(f"JSON → {p}")
    elif args.json:
        print(json.dumps(report.to_dict(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="echoreader",
        description="EchoReader — encrypted backup intake and readiness (read-only, no default decrypt).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("checks")
    p.set_defaults(func=cmd_checks)
    p = sub.add_parser("inspect")
    p.add_argument("path")
    p.add_argument("--out", default="")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inspect)
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
