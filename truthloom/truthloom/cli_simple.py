"""
Truthloom simple CLI — generate validation datasets.

  python -m truthloom generate --out ./truthloom_data
  python -m truthloom generate --android-only --out ./truthloom_data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from truthloom.synth import generate_all, generate_android_dump, generate_ios_backup


def cmd_generate(args: argparse.Namespace) -> int:
    out = Path(args.out or "truthloom_data")
    out.mkdir(parents=True, exist_ok=True)
    manifests = []
    if args.android_only:
        manifests = [generate_android_dump(out)]
        (out / "truthloom_index.json").write_text(
            json.dumps({"datasets": [manifests[0].to_dict()]}, indent=2),
            encoding="utf-8",
        )
        (out / f"{manifests[0].dataset_id}.json").write_text(
            json.dumps(manifests[0].to_dict(), indent=2), encoding="utf-8"
        )
    elif args.ios_only:
        manifests = [generate_ios_backup(out)]
        (out / "truthloom_index.json").write_text(
            json.dumps({"datasets": [manifests[0].to_dict()]}, indent=2),
            encoding="utf-8",
        )
        (out / f"{manifests[0].dataset_id}.json").write_text(
            json.dumps(manifests[0].to_dict(), indent=2), encoding="utf-8"
        )
    else:
        manifests = generate_all(out)
    print(f"Generated {len(manifests)} dataset(s) under {out}")
    for m in manifests:
        print(f"  {m.dataset_id}  ({m.kind})")
        print(f"    path: {m.path}")
        for g in m.ground_truth:
            print(f"    expect {g.artifact_type}: …{g.expected_summary_contains}…")
    print(f"Index → {out / 'truthloom_index.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="truthloom",
        description="Truthloom — generate synthetic validation datasets for LoKi parsers.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("generate", help="Create android + ios synthetic dumps")
    p.add_argument("--out", default="truthloom_data")
    p.add_argument("--android-only", action="store_true")
    p.add_argument("--ios-only", action="store_true")
    p.set_defaults(func=cmd_generate)
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
