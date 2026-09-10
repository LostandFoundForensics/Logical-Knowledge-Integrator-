"""
iDriller CLI — plain language.

  idriller list
  idriller inspect /path/to/ios_backup
  idriller extract /path/to/ios_backup --out ./case_out
  idriller extract /path/to/ios_backup --parsers sms,calls
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from idriller.core.backup import BackupRoot
from idriller.core.engine import list_parsers, run_extract
from idriller.export.writers import write_jsonl, write_summary_csv


def cmd_list(_args: argparse.Namespace) -> int:
    print("iDriller parsers (pick by id):\n")
    for p in list_parsers():
        print(f"  [{p['category']}]")
        print(f"    {p['id']:12}  {p['label']}")
        print(f"    {'':12}  {p['description']}\n")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    backup = BackupRoot(args.backup)
    print(f"Backup:      {backup.root}")
    print(f"Manifest.db: {backup.manifest_path}")
    info = backup.info_plist()
    print(f"Info.plist:  {info if info else '(not found)'}")
    with backup.open_manifest() as manifest:
        if not manifest.has_files_table():
            print("ERROR: Manifest.db has no Files table")
            return 1
        # Quick presence sample
        report = manifest.scan_presence(backup.root, sample_limit=5000)
        print(f"Manifest rows sampled: {report.total_records}")
        print(f"Payload files found:   {report.files_found}")
        print("\nInteresting paths in manifest:")
        for needle, label in (
            ("sms.db", "SMS database"),
            ("AddressBook", "Address Book"),
            ("CallHistory", "Call history"),
            ("CameraRoll", "Camera roll domain"),
        ):
            hits = manifest.find(relative_path_contains=needle, limit=3)
            if hits:
                for h in hits:
                    resolved = manifest.resolve_path(backup.root, h.file_id)
                    status = "on disk" if resolved else "missing on disk"
                    print(f"  {label:16}  {h.relative_path[:60]}  [{status}]")
            else:
                print(f"  {label:16}  (not in manifest sample)")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    parser_ids = None
    if args.parsers:
        parser_ids = [p.strip() for p in args.parsers.split(",") if p.strip()]
    print(f"Opening backup {args.backup} …")
    records = run_extract(
        args.backup,
        parser_ids=parser_ids,
        limit_per_parser=args.limit,
    )
    counts = Counter(r.artifact_type for r in records)
    print(f"Artifacts: {len(records)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")

    out = Path(args.out or Path(args.backup).name + "_idriller_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_jsonl(records, out / "artifacts.jsonl")
    csv_path = write_summary_csv(records, out / "summary.csv")
    meta = {
        "tool": "iDriller",
        "version": "1.0.0",
        "backup": str(Path(args.backup).resolve()),
        "artifact_count": len(records),
        "by_type": dict(counts),
        "parsers": parser_ids or [p["id"] for p in list_parsers()],
        "notes": [
            "Call direction (ZCALLTYPE) is best_effort/unverified when present.",
            "All evidence SQLite opened read-only.",
        ],
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL  → {jl}")
    print(f"CSV    → {csv_path}")
    print(f"Meta   → {out / 'run_meta.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="idriller",
        description="iDriller — parse an iOS backup folder (read-only).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="Show available parsers in plain language")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("inspect", help="Check Manifest.db and look for known artifacts")
    p.add_argument("backup", help="Path to iOS backup folder (contains Manifest.db)")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("extract", help="Extract artifacts from the backup")
    p.add_argument("backup")
    p.add_argument("--out", default="")
    p.add_argument("--parsers", default="", help="e.g. sms,calls,contacts")
    p.add_argument("--limit", type=int, default=50_000)
    p.set_defaults(func=cmd_extract)

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
