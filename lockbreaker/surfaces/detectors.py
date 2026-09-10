"""
Access surface detectors — original LockBreaker code.

A surface is a *lawful* capability already present (pairing trust, backup on disk,
ADB, extracted hash). Detectors only observe the host/evidence — they never bypass.
"""
from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SurfaceResult:
    surface_id: str
    label: str
    status: str                      # available | partially_available | not_available
    why: str
    what_it_unlocks: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    legal_note: str = ""
    risk_level: str = "low"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "label": self.label,
            "status": self.status,
            "why": self.why,
            "what_it_unlocks": self.what_it_unlocks,
            "limitations": self.limitations,
            "legal_note": self.legal_note,
            "risk_level": self.risk_level,
            "details": self.details,
        }


def detect_ios_pairing(_ctx: Dict[str, Any]) -> SurfaceResult:
    """Prior user trust on this host (lockdown pairing records)."""
    status, why, count = "not_available", "No pairing record found on this host.", 0
    system = platform.system()
    paths_checked: List[str] = []

    candidates: List[Path] = []
    if system == "Darwin":
        candidates = [Path("/var/db/lockdown")]
    elif system == "Linux":
        candidates = [Path("/var/lib/lockdown"), Path.home() / ".config" / "libimobiledevice"]
    elif system == "Windows":
        candidates = [
            Path.home() / "AppData" / "Roaming" / "Apple Computer" / "Lockdown",
        ]

    for folder in candidates:
        paths_checked.append(str(folder))
        if folder.is_dir():
            plists = list(folder.glob("*.plist"))
            count = len(plists)
            if count:
                status = "available"
                why = f"Trusted pairing record(s) found ({count})."
                break

    return SurfaceResult(
        surface_id="IOS-PAIRING-LOCKDOWN",
        label="iOS trusted pairing on this computer",
        status=status,
        why=why,
        what_it_unlocks=[
            "Talk to a previously trusted device without a new trust prompt",
            "May allow backup initiation if the device is connected",
        ],
        limitations=[
            "Does not unlock the device passcode",
            "Does not by itself decrypt an encrypted backup",
        ],
        legal_note="Relies on prior user trust established on this host. Not a security bypass.",
        risk_level="low",
        details={"records_found": count, "paths_checked": paths_checked},
    )


def detect_ios_backup_tools(_ctx: Dict[str, Any]) -> SurfaceResult:
    tools = {
        "idevicebackup2": shutil.which("idevicebackup2"),
        "idevice_id": shutil.which("idevice_id"),
        "cfgutil": shutil.which("cfgutil"),
    }
    found = {k: v for k, v in tools.items() if v}
    available = bool(found)
    return SurfaceResult(
        surface_id="IOS-BACKUP-TOOLS",
        label="iOS backup tools on PATH",
        status="available" if available else "not_available",
        why=(
            f"Found: {', '.join(found.keys())}"
            if found
            else "No idevicebackup2 / cfgutil found on PATH."
        ),
        what_it_unlocks=["Create or inspect iOS backups when a device is connected"],
        limitations=["Does not crack passwords", "Requires device trust / pairing"],
        legal_note="Standard manufacturer/community tooling only.",
        risk_level="low",
        details={"tools": tools},
    )


def detect_ios_backup_present(ctx: Dict[str, Any]) -> SurfaceResult:
    """Look for a backup folder or Manifest.db under evidence paths."""
    roots: List[Path] = []
    for key in ("evidence_root", "backup_path", "case_path"):
        raw = ctx.get(key)
        if raw:
            roots.append(Path(raw).expanduser())
    # Also scan common host backup locations (observe only)
    system = platform.system()
    if system == "Darwin":
        roots.append(Path.home() / "Library" / "Application Support" / "MobileSync" / "Backup")
    elif system == "Windows":
        roots.append(
            Path.home() / "AppData" / "Roaming" / "Apple Computer" / "MobileSync" / "Backup"
        )

    found: List[str] = []
    for root in roots:
        if not root.exists():
            continue
        if (root / "Manifest.db").is_file():
            found.append(str(root))
            continue
        if root.is_dir():
            for child in list(root.iterdir())[:50]:
                if child.is_dir() and (child / "Manifest.db").is_file():
                    found.append(str(child))

    return SurfaceResult(
        surface_id="IOS-BACKUP-PRESENT",
        label="iOS backup folder on disk",
        status="available" if found else "not_available",
        why=(
            f"Found {len(found)} backup folder(s) with Manifest.db."
            if found
            else "No Manifest.db-bearing backup folders found in checked paths."
        ),
        what_it_unlocks=["Parse backup with iDriller", "Possibly extract backup password hash"],
        limitations=["Encrypted backups still need the password to decrypt contents"],
        legal_note="Read-only inspection of files already on this host.",
        risk_level="low",
        details={"backups": found[:20]},
    )


def detect_adb(_ctx: Dict[str, Any]) -> SurfaceResult:
    adb = shutil.which("adb")
    return SurfaceResult(
        surface_id="ANDROID-ADB",
        label="Android Debug Bridge (adb)",
        status="available" if adb else "not_available",
        why=f"adb found at {adb}" if adb else "adb not on PATH.",
        what_it_unlocks=["Device communication when USB debugging is authorized"],
        limitations=["Requires user-authorized debugging", "Not a bypass of screen lock"],
        legal_note="Uses the official platform tool only when already present.",
        risk_level="low",
        details={"adb_path": adb},
    )


def detect_android_folder_dump(ctx: Dict[str, Any]) -> SurfaceResult:
    root = ctx.get("evidence_root") or ctx.get("android_dump")
    if not root:
        return SurfaceResult(
            surface_id="ANDROID-FOLDER-DUMP",
            label="Android folder dump",
            status="not_available",
            why="No evidence_root / android_dump path provided.",
            what_it_unlocks=["Parse with Android Excavator", "Locate locksettings / gesture key"],
            legal_note="Provide a path to an existing extract.",
            risk_level="low",
        )
    p = Path(root).expanduser()
    if not p.is_dir():
        return SurfaceResult(
            surface_id="ANDROID-FOLDER-DUMP",
            label="Android folder dump",
            status="not_available",
            why=f"Not a directory: {p}",
            what_it_unlocks=[],
            legal_note="",
            risk_level="low",
        )
    # Look for lock-related files without modifying anything
    hits = []
    for name in ("locksettings.db", "gesture.key", "password.key", "gatekeeper.pattern.key"):
        for match in p.rglob(name):
            if match.is_file():
                hits.append(str(match.relative_to(p)))
                if len(hits) >= 10:
                    break
        if len(hits) >= 10:
            break

    lock_db = any("locksettings" in h for h in hits)
    return SurfaceResult(
        surface_id="ANDROID-FOLDER-DUMP",
        label="Android folder dump",
        status="available" if p.is_dir() else "not_available",
        why=f"Folder present. Lock-related files found: {len(hits)}.",
        what_it_unlocks=["Offline parsing of extracted data"],
        limitations=["Quality depends on how the dump was acquired"],
        legal_note="Read-only walk of an existing extract.",
        risk_level="low",
        details={"lock_related": hits, "has_locksettings": lock_db},
    )


def detect_android_locksettings(ctx: Dict[str, Any]) -> SurfaceResult:
    """Subset: is locksettings.db actually present?"""
    dump = detect_android_folder_dump(ctx)
    has = bool(dump.details.get("has_locksettings"))
    return SurfaceResult(
        surface_id="ANDROID-LOCKSETTINGS",
        label="Android locksettings database",
        status="available" if has else "not_available",
        why=(
            "locksettings.db found under the folder dump."
            if has
            else "No locksettings.db found (run survey with evidence_root set)."
        ),
        what_it_unlocks=["Extract PIN/pattern hash material for authorized recovery"],
        limitations=["Hash format varies by Android version and OEM"],
        legal_note="Read-only open of evidence DB only after authorization for recovery profiles.",
        risk_level="medium",
        details=dump.details,
    )


def detect_hash_file(ctx: Dict[str, Any]) -> SurfaceResult:
    raw = ctx.get("hash_file")
    if not raw:
        return SurfaceResult(
            surface_id="HASH-FILE-PRESENT",
            label="Pre-extracted hash file",
            status="not_available",
            why="No hash_file path provided.",
            what_it_unlocks=["Direct wordlist / PIN attack against known hash"],
            legal_note="Operator supplies a hash obtained under separate authority.",
            risk_level="medium",
        )
    p = Path(raw).expanduser()
    ok = p.is_file()
    return SurfaceResult(
        surface_id="HASH-FILE-PRESENT",
        label="Pre-extracted hash file",
        status="available" if ok else "not_available",
        why=f"File {'found' if ok else 'not found'}: {p}",
        what_it_unlocks=["Authorized offline recovery attempts"],
        limitations=["Operator is responsible for lawful origin of the hash"],
        legal_note="Hash file is treated as evidence — never modified.",
        risk_level="medium",
        details={"path": str(p) if ok else None},
    )


ALL_DETECTORS = [
    detect_ios_pairing,
    detect_ios_backup_tools,
    detect_ios_backup_present,
    detect_adb,
    detect_android_folder_dump,
    detect_android_locksettings,
    detect_hash_file,
]
