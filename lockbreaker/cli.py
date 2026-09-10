"""
LockBreaker CLI — Access Surface Orchestrator.

  lockbreaker surfaces
  lockbreaker surfaces --evidence-root /path/to/dump
  lockbreaker profiles
  lockbreaker run survey_only --case ./case1
  lockbreaker run android_pattern --case ./case1 --evidence-root /dump \\
      --basis warrant --reference WR-2026-0142 --examiner "J. Doe"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lockbreaker.auth.gate import Authorization
from lockbreaker.doctrine.profiles import list_profiles
from lockbreaker.orchestrator import run_job
from lockbreaker.surfaces.survey import survey_access_surfaces, summarize_survey


def cmd_profiles(_args: argparse.Namespace) -> int:
    print("LockBreaker profiles (what you can request):\n")
    for p in list_profiles():
        print(f"  {p.profile_id}")
        print(f"    {p.label}")
        print(f"    {p.description}")
        print(f"    Authority required: {p.min_auth_basis}  ·  Risk: {p.risk_level}")
        if p.notes:
            print(f"    Note: {p.notes}")
        print()
    return 0


def cmd_surfaces(args: argparse.Namespace) -> int:
    ctx = {
        "evidence_root": args.evidence_root or None,
        "backup_path": args.backup or None,
        "hash_file": args.hash_file or None,
    }
    results = survey_access_surfaces(ctx)
    summary = summarize_survey(results)
    print("Access surface survey\n" + "=" * 40)
    for r in results:
        mark = {
            "available": "[OK]   ",
            "partially_available": "[PART] ",
            "not_available": "[--]   ",
        }.get(r.status, "[??]   ")
        print(f"{mark}{r.label}")
        print(f"         {r.why}")
        if r.what_it_unlocks:
            print(f"         Unlocks: {', '.join(r.what_it_unlocks[:2])}")
        print()
    print(
        f"Summary: {summary['available_count']} available · "
        f"{len(summary['partially_available'])} partial · "
        f"{len(summary['not_available'])} not available"
    )
    if args.json:
        print(json.dumps(summary, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    auth = None
    if args.profile != "survey_only":
        if not args.basis or not args.reference or not args.examiner:
            print(
                "ERROR: Recovery profiles require --basis, --reference, and --examiner.",
                file=sys.stderr,
            )
            return 2
        auth = Authorization(
            basis=args.basis,
            reference_id=args.reference,
            examiner=args.examiner,
            notes=args.auth_notes or "",
        )

    try:
        result = run_job(
            profile_id=args.profile,
            case_dir=args.case,
            auth=auth,
            evidence_root=args.evidence_root or None,
            backup_path=args.backup or None,
            hash_file=args.hash_file or None,
            wordlist=args.wordlist or None,
            examiner=args.examiner or "",
        )
    except PermissionError as e:
        print(f"AUTHORIZATION DENIED: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Profile:  {result['profile_id']}")
    print(f"Message:  {result.get('message', '')}")
    print(f"Found:    {result.get('found')}")
    print(f"Case:     {args.case}")
    print(f"Result:   {Path(args.case) / 'result.json'}")
    print(f"Audit:    {Path(args.case) / 'lockbreaker_audit.jsonl'}")
    if result.get("survey"):
        print(f"Surfaces available: {result['survey'].get('available_count', 0)}")
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lockbreaker",
        description=(
            "LockBreaker — Access Surface Orchestrator. "
            "Find lawful entry points first. Recover credentials only with authority."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("profiles", help="List recovery profiles in plain language")
    p.set_defaults(func=cmd_profiles)

    p = sub.add_parser("surfaces", help="Survey lawful access surfaces (always safe)")
    p.add_argument("--evidence-root", default="", help="Android folder dump path")
    p.add_argument("--backup", default="", help="iOS backup folder path")
    p.add_argument("--hash-file", default="", help="Pre-extracted hash file")
    p.add_argument("--json", action="store_true", help="Also print JSON summary")
    p.set_defaults(func=cmd_surfaces)

    p = sub.add_parser("run", help="Run a profile (survey_only needs no auth)")
    p.add_argument("profile", help="Profile id (see: lockbreaker profiles)")
    p.add_argument("--case", required=True, help="Case output folder")
    p.add_argument("--evidence-root", default="")
    p.add_argument("--backup", default="")
    p.add_argument("--hash-file", default="")
    p.add_argument("--wordlist", default="")
    p.add_argument("--basis", default="", help="owner_request|consent|warrant|court_order")
    p.add_argument("--reference", default="", help="Case/warrant/consent reference id")
    p.add_argument("--examiner", default="")
    p.add_argument("--auth-notes", default="")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
