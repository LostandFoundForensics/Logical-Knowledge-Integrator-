from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from echoreader.core.models import IntakeReport
from echoreader.inspect.android_ab import inspect_android_ab
from echoreader.inspect.ios_backup import inspect_ios_backup


def list_checks() -> List[Dict[str, str]]:
    return [
        {
            "id": "ios_backup",
            "label": "iOS backup folder",
            "description": "Manifest.db / Manifest.plist encryption and metadata.",
        },
        {
            "id": "android_ab",
            "label": "Android .ab file",
            "description": "ANDROID BACKUP header compression/encryption fields.",
        },
    ]


def inspect_path(path: str | Path) -> IntakeReport:
    path = Path(path).expanduser().resolve()
    if path.is_file() and path.suffix.lower() == ".ab":
        return inspect_android_ab(path)
    if path.is_file():
        # try ab header anyway
        report = inspect_android_ab(path)
        if report.kind == "android_ab":
            return report
        return IntakeReport(
            path=str(path),
            kind="unknown",
            encrypted=None,
            summary="File is not a recognized backup container.",
            warnings=["Pass an iOS backup folder or an Android .ab file."],
        )
    if path.is_dir():
        return inspect_ios_backup(path)
    return IntakeReport(
        path=str(path),
        kind="unknown",
        encrypted=None,
        summary="Path not found.",
        warnings=[f"Not found: {path}"],
    )
