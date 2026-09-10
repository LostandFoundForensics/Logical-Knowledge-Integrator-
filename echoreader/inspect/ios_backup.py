"""Inspect a standard iOS backup folder — read-only."""
from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from echoreader.core.models import IntakeReport


def _load_plist(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("rb") as f:
            data = plistlib.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def inspect_ios_backup(root: Path) -> IntakeReport:
    root = Path(root).resolve()
    findings: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}
    next_steps: List[str] = []

    manifest_db = root / "Manifest.db"
    if not manifest_db.is_file():
        hits = list(root.glob("[Mm]anifest.db"))
        manifest_db = hits[0] if hits else manifest_db

    has_manifest_db = manifest_db.is_file()
    details["manifest_db"] = str(manifest_db) if has_manifest_db else None
    if has_manifest_db:
        findings.append("Manifest.db present (file index available).")
    else:
        warnings.append("No Manifest.db — may not be a complete iTunes/Finder backup.")

    manifest_plist = None
    for name in ("Manifest.plist", "manifest.plist"):
        p = root / name
        if p.is_file():
            manifest_plist = p
            break
    details["manifest_plist"] = str(manifest_plist) if manifest_plist else None

    encrypted: Optional[bool] = None
    if manifest_plist:
        pl = _load_plist(manifest_plist)
        if pl is not None:
            encrypted = bool(pl.get("IsEncrypted") or pl.get("BackupKeyBag"))
            details["is_encrypted_flag"] = bool(pl.get("IsEncrypted"))
            details["has_backup_keybag"] = bool(pl.get("BackupKeyBag"))
            if encrypted:
                findings.append("Backup appears encrypted (IsEncrypted and/or BackupKeyBag).")
                next_steps.append(
                    "With lawful authority: LockBreaker profile ios_backup_hash "
                    "to extract password verifier (dry-run by default)."
                )
                next_steps.append(
                    "After password recovery (if authorized): unwrap then parse with iDriller / Recall Engine."
                )
            else:
                findings.append("Backup does not appear encrypted.")
                next_steps.append("Parse with iDriller (SMS/calls/contacts) and Recall Engine (notes/Safari/calendar).")
        else:
            warnings.append("Manifest.plist present but could not be parsed.")
    else:
        warnings.append("No Manifest.plist — encryption status unknown from plist.")
        if has_manifest_db:
            next_steps.append("Try iDriller inspect — Manifest.db alone may still allow path resolution.")

    info = None
    for name in ("Info.plist", "info.plist"):
        p = root / name
        if p.is_file():
            info = _load_plist(p)
            details["info_plist"] = str(p)
            break
    if info:
        for key in ("Device Name", "Product Type", "Product Version", "Serial Number", "Unique Identifier"):
            if key in info:
                details[key.replace(" ", "_").lower()] = str(info[key])
        findings.append("Info.plist metadata loaded (device fields if present).")

    status = None
    for name in ("Status.plist", "status.plist"):
        p = root / name
        if p.is_file():
            status = _load_plist(p)
            details["status_plist"] = str(p)
            break
    if status and "IsFullBackup" in status:
        details["is_full_backup"] = bool(status.get("IsFullBackup"))

    kind = "ios_backup"
    if not has_manifest_db and not manifest_plist:
        kind = "unknown"
        summary = "Path does not look like a standard iOS backup."
    elif encrypted:
        summary = "iOS backup present and appears encrypted."
    elif encrypted is False:
        summary = "iOS backup present and appears unencrypted."
    else:
        summary = "iOS backup-like folder; encryption status uncertain."

    return IntakeReport(
        path=str(root),
        kind=kind,
        encrypted=encrypted,
        summary=summary,
        findings=findings,
        next_steps=next_steps,
        details=details,
        warnings=warnings,
    )
