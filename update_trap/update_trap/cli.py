"""
Update Trap CLI — snapshot and diff folder extracts.

  python -m update_trap snapshot /path/to/dump --label before --out ./snap_before.json
  python -m update_trap snapshot /path/to/dump2 --label after --out ./snap_after.json
  python -m update_trap diff ./snap_before.json ./snap_after.json --out ./diff_out
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from update_trap.simple_diff import (
    build_snapshot,
    diff_snapshots,
    load_snapshot,
    save_snapshot,
)


def cmd_snapshot(args: argparse.Namespace) -> int:
    print(f"Snapshot {args.path} …")
    snap = build_snapshot(args.path, label=args.label or "", max_files=args.max_files)
    out = Path(args.out or f"snapshot_{snap.label or 'dump'}.json")
    save_snapshot(snap, out)
    print(f"Files: {len(snap.files)}")
    print(f"Wrote: {out}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    a = load_snapshot(Path(args.baseline))
    b = load_snapshot(Path(args.new))
    report = diff_snapshots(a, b)
    s = report.summary()
    print(f"Baseline: {report.baseline_label}")
    print(f"New:      {report.new_label}")
    print(f"Added:    {s['path_added']}")
    print(f"Removed:  {s['path_removed']}")
    print(f"Modified: {s['path_modified']}")
    print(f"Schema:   {s['schema_changes']}")
    for ch in report.path_changes[:30]:
        print(f"  [{ch.kind}] {ch.rel_path}")
    if len(report.path_changes) > 30:
        print(f"  … {len(report.path_changes) - 30} more path changes")
    for sc in report.schema_changes[:20]:
        print(f"  [schema] {sc.db_rel_path} :: {sc.table} :: {sc.change} {sc.details or ''}")
    out = Path(args.out or "update_trap_diff")
    out.mkdir(parents=True, exist_ok=True)
    (out / "diff.json").write_text(
        json.dumps(report.to_dict(), indent=2), encoding="utf-8"
    )
    print(f"JSON → {out / 'diff.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="update_trap",
        description="Update Trap — detect file and SQLite schema changes between extracts.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("snapshot", help="Hash files + SQLite schemas under a folder")
    p.add_argument("path")
    p.add_argument("--label", default="")
    p.add_argument("--out", default="")
    p.add_argument("--max-files", type=int, default=100_000)
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("diff", help="Diff two snapshot JSON files")
    p.add_argument("baseline")
    p.add_argument("new")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_diff)

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
