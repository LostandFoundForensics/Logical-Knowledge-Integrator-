"""
Sundial CLI — read a timeline without starting a web server.

  python -m sundial view --timeline ./bardo_timeline.json
  python -m sundial export --timeline ./bardo_timeline.json --out ./sundial_out
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sundial.simple_timeline import load_bardo_timeline, to_html, to_plain_text


def cmd_view(args: argparse.Namespace) -> int:
    events = load_bardo_timeline(Path(args.timeline))
    text = to_plain_text(events, case_id=args.case or "")
    if args.limit and args.limit > 0:
        # reprint with truncated events
        events = events[: args.limit]
        text = to_plain_text(events, case_id=args.case or "")
    print(text)
    print(f"({len(events)} events shown)", file=sys.stderr)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    events = load_bardo_timeline(Path(args.timeline))
    out = Path(args.out or "sundial_out")
    out.mkdir(parents=True, exist_ok=True)
    txt = to_plain_text(events, case_id=args.case or "")
    html = to_html(
        events,
        case_id=args.case or "",
        title=args.title or "Case timeline",
    )
    (out / "timeline.txt").write_text(txt, encoding="utf-8")
    (out / "timeline.html").write_text(html, encoding="utf-8")
    meta = {
        "tool": "Sundial",
        "version": "1.0.0-cli",
        "case_id": args.case or "",
        "event_count": len(events),
        "source": str(Path(args.timeline).resolve()),
        "notes": [
            "Observed events only in this export path.",
            "UTC used when converting unix milliseconds.",
        ],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Events: {len(events)}")
    print(f"TXT  → {out / 'timeline.txt'}")
    print(f"HTML → {out / 'timeline.html'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sundial",
        description="Sundial — simple timeline reader for LoKi exports (no server required).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("view", help="Print a plain-language timeline")
    p.add_argument("--timeline", required=True, help="Bardo timeline JSON")
    p.add_argument("--case", default="")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_view)

    p = sub.add_parser("export", help="Write timeline.txt and timeline.html")
    p.add_argument("--timeline", required=True)
    p.add_argument("--out", default="")
    p.add_argument("--case", default="")
    p.add_argument("--title", default="")
    p.set_defaults(func=cmd_export)

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
