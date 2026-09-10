"""
Chop Shop CLI.

  chopshop stations
  chopshop probe
  chopshop bench ./my_bench --case CASE-001 --examiner 'Jane Doe'
  chopshop recommend android
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from chopshop.core.bench import create_bench
from chopshop.core.probe import probe_environment
from chopshop.core.stations import list_stations


def cmd_stations(_args: argparse.Namespace) -> int:
    print("Chop Shop stations (recommended tool groups):\n")
    for s in list_stations():
        tools = ", ".join(s["tools"])  # type: ignore
        print(f"  {s['id']:10}  {s['label']}")
        print(f"  {'':10}  {s['description']}")
        print(f"  {'':10}  tools: {tools}\n")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    root = Path(args.loki_root) if args.loki_root else Path(__file__).resolve().parents[1]
    report = probe_environment(loki_root=root)
    print(f"Python: {report['python']}")
    print(f"Modules OK/Fail: {report['modules_ok']}/{report['modules_fail']}")
    for m in report["modules"]:
        status = "OK" if m["ok"] else "FAIL"
        extra = m.get("version") or m.get("error", "")
        print(f"  [{status}] {m['module']:22} {extra}")
    print("Host binaries:")
    for b in report["binaries"]:
        status = "OK" if b["ok"] else "—"
        print(f"  [{status}] {b['name']:10} {b.get('path') or ''}")
    print("Nested packages need extra PYTHONPATH:")
    for n in report["nested_pythonpath"]:
        print(f"  {n['module']:16}  (+ …/{n['hint']})")
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"JSON → {out}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    meta = create_bench(args.path, case_name=args.case or "", examiner=args.examiner or "")
    print(f"Bench created: {meta['bench_root']}")
    print(f"Case: {meta['case_name']}")
    print("Folders: evidence_links/ out/ notes/ exports/ logs/")
    print(f"Config → {Path(meta['bench_root']) / 'bench.json'}")
    print("\nNext: place path references in evidence_links/, then:")
    print("  python -m loki case <bench>/out/run1 --android <dump>")
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    stations = {s["id"]: s for s in list_stations()}
    s = stations.get(args.station)
    if not s:
        print(f"Unknown station: {args.station}", file=sys.stderr)
        print("Use: python -m chopshop stations", file=sys.stderr)
        return 2
    print(f"Station: {s['label']}")
    print(f"{s['description']}\n")
    print("Suggested order:")
    for i, tool in enumerate(s["tools"], 1):  # type: ignore
        print(f"  {i}. python -m {tool} …")
    print("\nOr from a bench:")
    print("  python -m loki case ./bench/out/run --android <dump>   # android station")
    print("  python -m loki case ./bench/out/run --ios <backup>     # ios station")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chopshop",
        description="Chop Shop — portable LoKi workbench (bench + environment probe).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("stations", help="List workbench stations")
    p.set_defaults(func=cmd_stations)

    p = sub.add_parser("probe", help="Check which tools import on this host")
    p.add_argument("--loki-root", default="", help="Path to loki_complete")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("bench", help="Create a case bench folder")
    p.add_argument("path")
    p.add_argument("--case", default="")
    p.add_argument("--examiner", default="")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("recommend", help="Recommend tools for a station")
    p.add_argument("station", help="intake|access|android|ios|bulk|case|qa")
    p.set_defaults(func=cmd_recommend)

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
