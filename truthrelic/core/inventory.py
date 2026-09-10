"""Walk a folder tree read-only and collect file metadata (+ optional hashes)."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import List, Optional

from truthrelic.core.hashing import sha256_file
from truthrelic.core.models import FileEntry


def inventory_tree(
    root: str | Path,
    *,
    hash_files: bool = False,
    max_hash_bytes: int = 0,
    max_entries: int = 200_000,
) -> List[FileEntry]:
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(root)

    entries: List[FileEntry] = []
    if root.is_file():
        st = root.stat()
        digest = ""
        if hash_files:
            digest = sha256_file(root, max_bytes=max_hash_bytes)
        entries.append(
            FileEntry(
                relative_path=root.name,
                size_bytes=st.st_size,
                mtime_epoch=st.st_mtime,
                mode_octal=oct(st.st_mode & 0o777),
                is_dir=False,
                sha256=digest,
            )
        )
        return entries

    for dirpath, dirnames, filenames in os.walk(root):
        # stable order
        dirnames.sort()
        filenames.sort()
        base = Path(dirpath)
        for name in dirnames + filenames:
            if len(entries) >= max_entries:
                return entries
            full = base / name
            try:
                st = full.lstat()
            except OSError:
                continue
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                rel = str(full)
            is_dir = stat.S_ISDIR(st.st_mode)
            digest = ""
            notes = ""
            if hash_files and not is_dir and stat.S_ISREG(st.st_mode):
                try:
                    digest = sha256_file(full, max_bytes=max_hash_bytes)
                    if max_hash_bytes and st.st_size > max_hash_bytes:
                        notes = f"partial_hash_first_{max_hash_bytes}_bytes"
                except OSError:
                    notes = "hash_failed"
            entries.append(
                FileEntry(
                    relative_path=rel,
                    size_bytes=st.st_size if not is_dir else 0,
                    mtime_epoch=st.st_mtime,
                    mode_octal=oct(st.st_mode & 0o777),
                    is_dir=is_dir,
                    sha256=digest,
                    notes=notes,
                )
            )
    return entries
