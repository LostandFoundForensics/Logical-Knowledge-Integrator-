"""
Nimbus Bridge CLI — local cloud export intake.

  python -m nimbus_bridge recognize /path/to/Takeout
  python -m nimbus_bridge scan /path/to/Takeout --out ./nb_out
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from nimbus_bridge.simple_intake import recognize, scan_export


def cmd_recognize(args: argparse.Namespace) -> int:
    info = recognize(Path(args.path))
    print(json.dumps(info, indent=2))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    print(f"Scanning cloud export {args.path} (read-only) …")
    hits = scan_export(args.path, limit=args.limit)
    counts = Counter(h.artifact_type for h in hits)
    print(f"Artifacts: {len(hits)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    out = Path(args.out or "nimbus_bridge_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = out / "artifacts.jsonl"
    with jl.open("w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h.to_dict(), ensure_ascii=False) + "\n")
    meta = {
        "tool": "NimbusBridge",
        "version": "1.0.0-cli",
        "path": str(Path(args.path).resolve()),
        "count": len(hits),
        "by_type": dict(counts),
        "notes": [
            "Local export only — no live cloud API calls.",
            "Evidence/export tree not modified.",
        ],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL → {jl}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nimbus_bridge",
        description="Nimbus Bridge — intake Google Takeout-style local exports (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("recognize", help="Detect Takeout-like structure")
    p.add_argument("path")
    p.set_defaults(func=cmd_recognize)
    p = sub.add_parser("scan", help="Parse contacts + activity into JSONL")
    p.add_argument("path")
    p.add_argument("--out", default="")
    p.add_argument("--limit", type=int, default=50_000)
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
