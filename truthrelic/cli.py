"""
Truth Relic CLI — plain language.

  truthrelic actions
  truthrelic inventory /path/to/folder --out ./tr_out
  truthrelic inventory /path --hash --out ./tr_out
  truthrelic probe /path/to/disk.img --out ./tr_out
  truthrelic hash /path/to/file
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from truthrelic.core.engine import list_actions
from truthrelic.core.hashing import sha256_file
from truthrelic.core.inventory import inventory_tree
from truthrelic.export.writers import write_inventory_jsonl, write_probe_json
from truthrelic.probe.image import probe_image


def cmd_actions(_args: argparse.Namespace) -> int:
    print("Truth Relic actions:\n")
    for a in list_actions():
        print(f"  {a['id']:12}  {a['label']}")
        print(f"  {'':12}  {a['description']}\n")
    return 0


def cmd_inventory(args: argparse.Namespace) -> int:
    print(f"Inventory {args.path} (read-only) …")
    entries = inventory_tree(
        args.path,
        hash_files=args.hash,
        max_hash_bytes=args.max_hash_bytes,
        max_entries=args.max_entries,
    )
    files = sum(1 for e in entries if not e.is_dir)
    dirs = sum(1 for e in entries if e.is_dir)
    print(f"Entries: {len(entries)} ({files} files, {dirs} dirs)")
    out = Path(args.out or "truthrelic_out")
    out.mkdir(parents=True, exist_ok=True)
    jl = write_inventory_jsonl(entries, out / "inventory.jsonl")
    meta = {
        "tool": "TruthRelic",
        "version": "1.0.0",
        "path": str(Path(args.path).resolve()),
        "entry_count": len(entries),
        "files": files,
        "dirs": dirs,
        "hashed": bool(args.hash),
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"JSONL → {jl}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    print(f"Probing image {args.path} (read-only, no mount) …")
    probe = probe_image(args.path)
    print(f"Size:       {probe.size_bytes} bytes")
    print(f"Scheme:     {probe.scheme}")
    print(f"Partitions: {len(probe.partitions)}")
    for p in probe.partitions[:20]:
        name = f" ({p.name})" if p.name else ""
        print(f"  [{p.index}] LBA {p.start_lba} size {p.size_lba} → {p.type_hint}{name}")
    if probe.fs_hints:
        print("FS hints:")
        for h in probe.fs_hints:
            print(f"  {h}")
    for n in probe.notes:
        print(f"Note: {n}")
    out = Path(args.out or "truthrelic_out")
    out.mkdir(parents=True, exist_ok=True)
    path = write_probe_json(probe, out / "probe.json")
    print(f"JSON → {path}")
    return 0


def cmd_hash(args: argparse.Namespace) -> int:
    p = Path(args.path)
    digest = sha256_file(p)
    print(f"SHA-256  {digest}  {p}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="truthrelic",
        description="Truth Relic — read-only filesystem inventory and disk image probe.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("actions", help="List actions")
    p.set_defaults(func=cmd_actions)

    p = sub.add_parser("inventory", help="Inventory a folder or file")
    p.add_argument("path")
    p.add_argument("--out", default="")
    p.add_argument("--hash", action="store_true", help="SHA-256 each regular file")
    p.add_argument("--max-hash-bytes", type=int, default=0, help="0 = full file")
    p.add_argument("--max-entries", type=int, default=200_000)
    p.set_defaults(func=cmd_inventory)

    p = sub.add_parser("probe", help="Probe a disk image (MBR/GPT + FS hints)")
    p.add_argument("path")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("hash", help="SHA-256 one file")
    p.add_argument("path")
    p.set_defaults(func=cmd_hash)

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
