"""
LoKi operator CLI.

  python -m loki tools
  python -m loki how <tool_id>
  python -m loki case ./case1 --android /path/dump --ios /path/backup
  python -m loki case ./case1 --android /path/dump --takeout /path/Takeout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from loki.catalog import list_tools
from loki.pipeline import run_case


def cmd_tools(_args: argparse.Namespace) -> int:
    print("LoKi operational tools:\n")
    print(f"  {'id':22}  {'label':22}  role")
    print(f"  {'-'*22}  {'-'*22}  ----")
    for t in list_tools():
        print(f"  {t.tool_id:22}  {t.label:22}  {t.role}")
    print("\nRun a single tool with:")
    print("  PYTHONPATH=<loki_complete>[/subdir] python -m <module> …")
    return 0


def cmd_how(args: argparse.Namespace) -> int:
    tools = {t.tool_id: t for t in list_tools()}
    t = tools.get(args.tool_id)
    if not t:
        print(f"Unknown tool: {args.tool_id}", file=sys.stderr)
        print("Use: python -m loki tools", file=sys.stderr)
        return 2
    print(f"{t.label} ({t.tool_id})")
    print(f"  Role:   {t.role}")
    print(f"  Module: python -m {t.module}")
    if t.pythonpath_hint:
        print(f"  PYTHONPATH must include loki_complete/{t.pythonpath_hint}")
    else:
        print("  PYTHONPATH must include loki_complete/")
    print("  Examples:")
    examples = {
        "android_excavator": "python -m android_excavator scan /dump --out ./out",
        "idriller": "python -m idriller scan /ios_backup --out ./out",
        "lockbreaker": "python -m lockbreaker surfaces /path",
        "bardo": "python -m bardo status --case ./case",
        "witness_light": "python -m witness_light draft --artifacts ./artifacts.jsonl --out ./wl",
        "truthloom": "python -m truthloom generate --out ./truthloom_data",
        "sundial": "python -m sundial export --timeline ./timeline.json --out ./sd",
        "update_trap": "python -m update_trap snapshot /dump --label before --out snap.json",
        "nimbus_bridge": "python -m nimbus_bridge scan /Takeout --out ./nb",
    }
    print(f"    {examples.get(t.tool_id, 'python -m ' + t.module + ' --help')}")
    return 0


def cmd_case(args: argparse.Namespace) -> int:
    if not args.android and not args.ios and not args.takeout:
        print("Provide at least one of --android, --ios, --takeout", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    summary = run_case(
        Path(args.case_dir),
        android_dump=Path(args.android) if args.android else None,
        ios_backup=Path(args.ios) if args.ios else None,
        takeout=Path(args.takeout) if args.takeout else None,
        root=root,
    )
    print(f"Case: {summary['case_dir']}")
    print(f"OK:   {summary['ok_count']}  Fail: {summary['fail_count']}")
    for s in summary["steps"]:
        status = "OK" if s.get("ok") else "FAIL"
        print(f"  [{status}] {s.get('module')}")
        if not s.get("ok") and s.get("stderr_tail"):
            err = s["stderr_tail"].strip().splitlines()[-1:] 
            if err:
                print(f"         {err[0][:120]}")
    print(f"Report → {Path(args.case_dir) / 'pipeline_report.json'}")
    return 0 if summary["fail_count"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="loki",
        description="LoKi — Lost & Found forensics operator CLI.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("tools", help="List operational tools")
    p.set_defaults(func=cmd_tools)

    p = sub.add_parser("how", help="How to run a tool")
    p.add_argument("tool_id")
    p.set_defaults(func=cmd_how)

    p = sub.add_parser("case", help="Run minimal multi-tool case pipeline")
    p.add_argument("case_dir")
    p.add_argument("--android", default="", help="Android folder dump")
    p.add_argument("--ios", default="", help="iOS backup folder")
    p.add_argument("--takeout", default="", help="Google Takeout folder")
    p.set_defaults(func=cmd_case)

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
