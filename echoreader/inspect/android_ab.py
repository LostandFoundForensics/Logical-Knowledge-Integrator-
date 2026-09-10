"""
Inspect Android backup (.ab) header — read-only.

Format is a textual header then optional compressed/encrypted payload.
We only read the first few KB to classify — never decrypt here.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from echoreader.core.models import IntakeReport


def inspect_android_ab(path: Path) -> IntakeReport:
    path = Path(path).resolve()
    findings: List[str] = []
    warnings: List[str] = []
    next_steps: List[str] = []
    details = {"size_bytes": path.stat().st_size if path.is_file() else 0}

    encrypted: Optional[bool] = None
    kind = "android_ab"

    if not path.is_file():
        return IntakeReport(
            path=str(path),
            kind="unknown",
            encrypted=None,
            summary="Not a file.",
            warnings=["Path is not a file."],
        )

    # Read small prefix only
    with path.open("rb") as f:
        prefix = f.read(2048)

    try:
        text = prefix.decode("utf-8", errors="replace")
    except Exception:
        text = ""

    if not text.startswith("ANDROID BACKUP"):
        return IntakeReport(
            path=str(path),
            kind="unknown",
            encrypted=None,
            summary="File does not start with ANDROID BACKUP header.",
            warnings=["Not a recognized Android .ab backup header."],
            details=details,
        )

    findings.append("ANDROID BACKUP header recognized.")
    lines = text.splitlines()
    details["header_lines"] = lines[:5]

    # Typical lines: ANDROID BACKUP / 1 / 1 / none|AES-256
    compression = None
    encryption = None
    if len(lines) >= 4:
        try:
            details["version"] = lines[1].strip()
        except Exception:
            pass
        compression = lines[2].strip() if len(lines) > 2 else None
        encryption = lines[3].strip() if len(lines) > 3 else None
        details["compression"] = compression
        details["encryption"] = encryption

    if encryption and encryption.lower() not in ("none", ""):
        encrypted = True
        findings.append(f"Encryption field: {encryption}")
        next_steps.append(
            "Encrypted Android backups need the backup password and a lawful recovery path "
            "(not performed by EchoReader by default)."
        )
    else:
        encrypted = False
        findings.append("Encryption field indicates none (or missing).")
        next_steps.append(
            "Unencrypted .ab may be unpacked with platform tools into a folder dump, "
            "then parsed with Android Excavator / Memory Snare."
        )

    summary = (
        "Android .ab backup appears encrypted."
        if encrypted
        else "Android .ab backup appears unencrypted (header)."
    )
    return IntakeReport(
        path=str(path),
        kind=kind,
        encrypted=encrypted,
        summary=summary,
        findings=findings,
        next_steps=next_steps,
        details=details,
        warnings=warnings,
    )
