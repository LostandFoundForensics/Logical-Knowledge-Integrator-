"""
FolderDump — index files under an Android extract root.

Typical inputs:
  - adb pull /data/... output
  - unpacked nandroid / userdata partition tree
  - any directory tree containing app databases
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple


class FolderDump:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"Folder dump root not found: {self.root}")
        self._index: Dict[str, Path] = {}
        self._scanned = False

    def scan(self, *, max_files: int = 500_000) -> int:
        """Walk the tree once. Relative paths use forward slashes."""
        self._index.clear()
        n = 0
        for dirpath, _dirnames, filenames in os.walk(self.root):
            for fn in filenames:
                if n >= max_files:
                    break
                full = Path(dirpath) / fn
                try:
                    rel = full.relative_to(self.root).as_posix()
                except ValueError:
                    continue
                try:
                    if full.is_file():
                        self._index[rel] = full
                        n += 1
                except OSError:
                    continue
            if n >= max_files:
                break
        self._scanned = True
        return n

    def ensure_scanned(self) -> None:
        if not self._scanned:
            self.scan()

    def find_by_name(self, name: str, *, case_insensitive: bool = True) -> List[Path]:
        """Find files whose basename matches (e.g. mmssms.db)."""
        self.ensure_scanned()
        target = name.lower() if case_insensitive else name
        out: List[Path] = []
        for rel, full in self._index.items():
            base = Path(rel).name
            if case_insensitive:
                if base.lower() == target:
                    out.append(full)
            elif base == target:
                out.append(full)
        return out

    def find_path_contains(self, fragment: str) -> List[Path]:
        """Find files whose relative path contains a fragment."""
        self.ensure_scanned()
        frag = fragment.lower()
        return [full for rel, full in self._index.items() if frag in rel.lower()]

    def logical_path(self, real: Path) -> str:
        try:
            return real.relative_to(self.root).as_posix()
        except ValueError:
            return str(real)

    def sha256_file(self, path: Path, *, chunk: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                b = f.read(chunk)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()

    @property
    def file_count(self) -> int:
        self.ensure_scanned()
        return len(self._index)
