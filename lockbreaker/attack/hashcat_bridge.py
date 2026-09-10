"""
Optional Hashcat bridge.

Only activates when LOCKBREAKER_ENABLE_REAL_BACKENDS=1.
Never uses shell=True. Mode map is doctrine-fixed, not user-arbitrary.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from lockbreaker.attack.dry_run import run_dry_run

# Doctrine-fixed modes — not free-form user input
HASHCAT_MODE_MAP = {
    "android_pin": 5800,          # Android PIN (example family — verify against target hash)
    "android_pattern": 5800,
    "generic_md5": 0,
    "generic_sha1": 100,
    "generic_sha256": 1400,
    "itunes_backup": 14800,       # iTunes backup
}


def real_backends_enabled() -> bool:
    return os.environ.get("LOCKBREAKER_ENABLE_REAL_BACKENDS", "0").strip() == "1"


def run_hashcat_phase(
    *,
    profile_id: str,
    strategy: str,
    artifacts: List[Dict[str, Any]],
    work_dir: Path,
    wordlist: Optional[Path] = None,
    max_runtime_minutes: int = 30,
) -> Dict[str, Any]:
    if not real_backends_enabled():
        return run_dry_run(
            profile_id=profile_id,
            strategy=strategy,
            artifacts=artifacts,
        )

    hc = os.environ.get("LOCKBREAKER_HASHCAT_BIN") or shutil.which("hashcat")
    if not hc:
        return {
            "ok": False,
            "found": False,
            "backend": "hashcat",
            "message": "Real backends enabled but hashcat binary not found.",
            "findings": [],
            "near_misses": [],
        }

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    hash_arts = [
        a for a in artifacts
        if a.get("kind") in (
            "pattern_hash",
            "legacy_gesture_hash",
            "legacy_password_hashcat",
            "ios_backup_hash",
            "hash_file",
            "gatekeeper_blob",
        )
    ]
    if not hash_arts:
        return {
            "ok": False,
            "found": False,
            "backend": "hashcat",
            "message": "No hash artifact suitable for hashcat in this phase.",
            "findings": [],
            "near_misses": [],
        }

    primary = hash_arts[0]
    if primary.get("kind") == "ios_backup_hash":
        mode = int(primary.get("hashcat_mode") or HASHCAT_MODE_MAP["itunes_backup"])
    elif strategy == "pattern":
        mode = HASHCAT_MODE_MAP.get("android_pattern", 5800)
    elif strategy in ("pin_4", "pin_6"):
        mode = HASHCAT_MODE_MAP.get("android_pin", 5800)
    else:
        mode = HASHCAT_MODE_MAP.get("generic_sha1", 100)
    outfile = work_dir / "hashcat.potfile"
    cmd = [
        hc,
        f"--hash-type={mode}",
        "--status",
        "--outfile", str(outfile),
        "--outfile-format=2",
        "--potfile-disable",
        primary["path"],
    ]
    if wordlist and Path(wordlist).is_file():
        cmd.extend(["--attack-mode=0", str(wordlist)])
    else:
        # Minimal mask for pin_4 only when strategy says so
        if strategy == "pin_4":
            cmd.extend(["--attack-mode=3", "?d?d?d?d"])
        elif strategy == "pin_6":
            cmd.extend(["--attack-mode=3", "?d?d?d?d?d?d"])
        else:
            return {
                "ok": False,
                "found": False,
                "backend": "hashcat",
                "message": "No wordlist provided and strategy is not a simple PIN mask.",
                "findings": [],
                "near_misses": [],
            }

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(60, max_runtime_minutes * 60),
            check=False,
        )
    except subprocess.TimeoutExpired:
        pass

    findings = []
    if outfile.exists():
        for line in outfile.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ":" in line:
                findings.append(line.strip())

    return {
        "ok": True,
        "found": bool(findings),
        "backend": "hashcat",
        "message": f"Hashcat phase finished (mode={mode}).",
        "findings": findings[:50],
        "near_misses": [],
        "artifacts": {"outfile": str(outfile)},
    }
