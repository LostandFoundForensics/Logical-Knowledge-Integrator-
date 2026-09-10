"""
Ghostframe CLI — intentionally simple.

  ghostframe list
  ghostframe run /path/to/memory.dmp --plugins processes,network
  ghostframe hash /path/to/memory.dmp
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ghostframe.core.run_engine import RunEngine
from ghostframe.registry import default_registry


def cmd_list(_args: argparse.Namespace) -> int:
    reg = default_registry()
    print("Ghostframe plugins (pick by id):\n")
    by_cat = reg.by_category()
    for cat in sorted(by_cat):
        print(f"  [{cat}]")
        for p in by_cat[cat]:
            vol = " (needs Volatility 3)" if p.spec.requires_volatility else ""
            print(f"    {p.spec.plugin_id:16}  {p.spec.label}{vol}")
            print(f"    {'':16}  {p.spec.description}")
        print()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    engine = RunEngine()
    ctx = engine.prepare_context(
        args.image,
        case_id=args.case_id or "",
        output_dir=args.output or "",
        os_hint=args.os or "",
    )
    print(f"Evidence: {ctx.evidence_path}")
    print(f"SHA-256:  {ctx.evidence_sha256}")
    print(f"Output:   {ctx.output_dir}")

    plugin_ids = [p.strip() for p in args.plugins.split(",") if p.strip()]
    if not plugin_ids:
        plugin_ids = ["hash", "processes"]

    print(f"Running:  {', '.join(plugin_ids)}")
    results = engine.run_many(ctx, plugin_ids)
    out = engine.write_results(ctx, results)
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"  [{status}] {r.plugin_id}: {r.row_count} row(s)")
        for w in r.warnings[:3]:
            print(f"         ! {w}")
    print(f"Wrote observations → {out}")
    return 0 if all(r.ok for r in results) else 1


def cmd_hash(args: argparse.Namespace) -> int:
    engine = RunEngine()
    ctx = engine.prepare_context(args.image, output_dir=args.output or "")
    result = engine.run_one(ctx, "hash")
    print(json.dumps(result.rows[0] if result.rows else {}, indent=2))
    return 0 if result.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ghostframe",
        description="Ghostframe — look inside a memory capture (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Show available plugins in plain language")
    p_list.set_defaults(func=cmd_list)

    p_run = sub.add_parser("run", help="Run plugins against a memory image")
    p_run.add_argument("image", help="Path to the memory capture file")
    p_run.add_argument(
        "--plugins",
        default="hash,processes",
        help="Comma-separated plugin ids (default: hash,processes)",
    )
    p_run.add_argument("--case-id", default="")
    p_run.add_argument("--output", default="", help="Folder for observations (created if needed)")
    p_run.add_argument("--os", default="", help="Optional hint: windows|linux|mac")
    p_run.set_defaults(func=cmd_run)

    p_hash = sub.add_parser("hash", help="Fingerprint a memory file only")
    p_hash.add_argument("image")
    p_hash.add_argument("--output", default="")
    p_hash.set_defaults(func=cmd_hash)

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
