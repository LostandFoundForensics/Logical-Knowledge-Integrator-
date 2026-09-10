"""
BackupRoot — a standard iOS backup folder.

Expected layout:
  Manifest.db, Info.plist, Status.plist, Manifest.plist
  xx/<fileID> payload files
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from idriller.core.manifest import ManifestDB


class BackupRoot:
    def __init__(self, path: str | Path) -> None:
        self.root = Path(path).expanduser().resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"Backup folder not found: {self.root}")
        self.manifest_path = self.root / "Manifest.db"
        if not self.manifest_path.is_file():
            # case-insensitive search
            hits = list(self.root.glob("[Mm]anifest.db"))
            if hits:
                self.manifest_path = hits[0]
            else:
                raise FileNotFoundError(
                    f"No Manifest.db in {self.root}. "
                    "Point iDriller at an iTunes/Finder backup folder."
                )

    def open_manifest(self) -> ManifestDB:
        return ManifestDB.open(self.manifest_path)

    def info_plist(self) -> Optional[Path]:
        for name in ("Info.plist", "info.plist"):
            p = self.root / name
            if p.is_file():
                return p
        return None

    def sha256_file(self, path: Path, *, chunk: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                b = f.read(chunk)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
