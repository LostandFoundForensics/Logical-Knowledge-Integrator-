"""
Diamond Forger CLI.

  diamond_forger formats
  diamond_forger check '<hashline>'              # dry-run
  diamond_forger check '<hashline>' --execute \\
      --examiner 'Jane Doe' --authority 'Warrant 2024-001' \\
      --wordlist ./words.txt --out ./df_out
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from diamond_forger.core.engine import dictionary_check, dry_run, list_formats, validate_hash_line
from diamond_forger.export.writers import write_result_json


def cmd_formats(_args: argparse.Namespace) -> int:
    print("Supported hash line formats:\n")
    for f in list_formats():
        print(f"  {f['id']:16}  {f['label']}")
        print(f"  {'':16}  {f['description']}\n")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    line = args.hash_line
    if args.hash_file:
        line = Path(args.hash_file).read_text(encoding="utf-8").splitlines()[0].strip()
    if not args.execute:
        result = dry_run(line)
    else:
        result = dictionary_check(
            line,
            Path(args.wordlist),
            examiner=args.examiner or "",
            authority=args.authority or "",
            max_attempts=args.max_attempts,
        )
    print(f"Mode:     {result.mode}")
    print(f"Format:   {result.format_id}")
    print(f"Accepted: {result.accepted}")
    print(f"Message:  {result.message}")
    if result.recovered:
        print("Recovered: yes (plaintext written only to --out JSON if requested)")
    for w in result.warnings:
        print(f"Warning:  {w}")
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        # redact plaintext from console; keep in file for authorized examiner
        p = write_result_json(result, out / "result.json")
        meta = {
            "tool": "DiamondForger",
            "version": "1.0.0",
            "examiner": args.examiner if args.execute else None,
            "authority": args.authority if args.execute else None,
        }
        (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"JSON → {p}")
    return 0 if result.accepted or result.mode == "dry_run" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="diamond_forger",
        description="Diamond Forger — authorized hash recovery (dry-run by default).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("formats")
    p.set_defaults(func=cmd_formats)
    p = sub.add_parser("check")
    p.add_argument("hash_line", nargs="?", default="")
    p.add_argument("--hash-file", default="")
    p.add_argument("--execute", action="store_true", help="Run dictionary check (requires authority)")
    p.add_argument("--examiner", default="")
    p.add_argument("--authority", default="")
    p.add_argument("--wordlist", default="")
    p.add_argument("--max-attempts", type=int, default=10_000)
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_check)
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
