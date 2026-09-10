"""
Witness Light CLI.

  witness_light classes
  witness_light draft --bardo-timeline ./timeline.json --out ./wl_out
  witness_light draft --artifacts ./artifacts.jsonl --case CASE-001 --out ./wl_out
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from witness_light.core.engine import draft_report, list_sentence_classes
from witness_light.export.writers import write_report_json, write_report_txt
from witness_light.loaders.bardo import load_bardo_timeline
from witness_light.loaders.jsonl_artifacts import load_artifacts_jsonl


def cmd_classes(_args: argparse.Namespace) -> int:
    print("Allowed sentence classes (only these are generated):\n")
    for c in list_sentence_classes():
        print(f"  - {c}")
    print("\nIntent, motive, and guilt conclusions are not generated.")
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    events = []
    artifacts = []
    if args.bardo_timeline:
        events = load_bardo_timeline(Path(args.bardo_timeline))
        print(f"Loaded {len(events)} timeline events")
    if args.artifacts:
        artifacts = load_artifacts_jsonl(Path(args.artifacts))
        print(f"Loaded {len(artifacts)} artifact rows")
    if not events and not artifacts:
        print("Provide --bardo-timeline and/or --artifacts", file=sys.stderr)
        return 2

    report = draft_report(
        case_id=args.case or "",
        title=args.title or "Draft observation report",
        events=events,
        artifacts=artifacts,
        max_observed=args.max_observed,
    )
    out = Path(args.out or "witness_light_out")
    out.mkdir(parents=True, exist_ok=True)
    t = write_report_txt(report, out / "draft_report.txt")
    j = write_report_json(report, out / "draft_report.json")
    print(f"Observed lines: {report.stats.get('observed_lines')}")
    print(f"TXT  → {t}")
    print(f"JSON → {j}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="witness_light",
        description="Witness Light — court-safe draft language from tool exports (no evidence access).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("classes", help="List allowed sentence classes")
    p.set_defaults(func=cmd_classes)

    p = sub.add_parser("draft", help="Generate a draft report from exports")
    p.add_argument("--bardo-timeline", default="", help="Bardo timeline JSON")
    p.add_argument("--artifacts", default="", help="Excavator/iDriller artifacts.jsonl")
    p.add_argument("--case", default="")
    p.add_argument("--title", default="")
    p.add_argument("--out", default="")
    p.add_argument("--max-observed", type=int, default=200)
    p.set_defaults(func=cmd_draft)

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
