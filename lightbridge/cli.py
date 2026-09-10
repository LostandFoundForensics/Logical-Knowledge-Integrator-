"""
LightBridge CLI.

  lightbridge tools
  lightbridge devices
  lightbridge info <udid>
  lightbridge guide
  lightbridge backup <udid> --dest ./bk --examiner X --authority Y   # dry-run
  lightbridge backup <udid> --dest ./bk --examiner X --authority Y --execute
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lightbridge.core.engine import (
    backup_guidance,
    device_info,
    list_actions,
    list_devices,
    probe_host_tools,
    request_backup,
)


def cmd_actions(_args: argparse.Namespace) -> int:
    for a in list_actions():
        print(f"  {a['id']:10}  {a['label']}")
        print(f"  {'':10}  {a['description']}\n")
    return 0


def cmd_tools(args: argparse.Namespace) -> int:
    t = probe_host_tools()
    print("libimobiledevice-style host tools:\n")
    for name, path in [
        ("idevice_id", t.idevice_id),
        ("ideviceinfo", t.ideviceinfo),
        ("idevicepair", t.idevicepair),
        ("idevicebackup2", t.idevicebackup2),
        ("ideviceinstaller", t.ideviceinstaller),
    ]:
        status = path or "(not found)"
        print(f"  {name:18}  {status}")
    for n in t.notes:
        print(f"\nNote: {n}")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(t.to_dict(), indent=2), encoding="utf-8")
        print(f"JSON → {args.out}")
    return 0


def cmd_devices(args: argparse.Namespace) -> int:
    tools = probe_host_tools()
    if not tools.idevice_id:
        print("No idevice_id on PATH — cannot list USB devices.")
        print("Use an offline backup with EchoReader / iDriller instead.")
        return 0
    devices = list_devices()
    if not devices:
        print("No devices reported (none attached, trust dialog, or usbmux issue).")
        return 0
    print(f"Devices: {len(devices)}")
    for d in devices:
        print(f"  {d.udid}")
    if args.out:
        Path(args.out).write_text(
            json.dumps([d.to_dict() for d in devices], indent=2), encoding="utf-8"
        )
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    info = device_info(args.udid)
    if info is None:
        print("ideviceinfo not available or failed.", file=sys.stderr)
        return 2
    print(f"UDID:    {info.udid}")
    print(f"Name:    {info.name}")
    print(f"Type:    {info.product_type}")
    print(f"Version: {info.product_version}")
    if args.out:
        Path(args.out).write_text(json.dumps(info.to_dict(), indent=2), encoding="utf-8")
        print(f"JSON → {args.out}")
    return 0


def cmd_guide(_args: argparse.Namespace) -> int:
    print("LightBridge backup / parse guidance:\n")
    for line in backup_guidance():
        print(f"  • {line}")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    result = request_backup(
        args.udid,
        Path(args.dest),
        examiner=args.examiner or "",
        authority=args.authority or "",
        execute=bool(args.execute),
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lightbridge",
        description="LightBridge — iOS USB/tool surface (libimobiledevice host bridge).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("actions")
    p.set_defaults(func=cmd_actions)

    p = sub.add_parser("tools", help="Probe host idevice* tools")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_tools)

    p = sub.add_parser("devices", help="List UDIDs")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_devices)

    p = sub.add_parser("info", help="ideviceinfo for one UDID")
    p.add_argument("udid")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("guide", help="Offline backup parse guidance")
    p.set_defaults(func=cmd_guide)

    p = sub.add_parser("backup", help="Optional idevicebackup2 (dry-run default)")
    p.add_argument("udid")
    p.add_argument("--dest", required=True)
    p.add_argument("--examiner", default="")
    p.add_argument("--authority", default="")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(func=cmd_backup)

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
