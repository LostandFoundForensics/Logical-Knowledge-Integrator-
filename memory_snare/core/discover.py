from __future__ import annotations

import os
from pathlib import Path
from typing import List


def find_named(root: Path, names: tuple, *, limit: int = 50) -> List[Path]:
    root = Path(root)
    found: List[Path] = []
    lower = {n.lower() for n in names}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower() in lower or fn in names:
                found.append(Path(dirpath) / fn)
                if len(found) >= limit:
                    return found
    return found


def find_path_contains(root: Path, fragment: str, *, limit: int = 50) -> List[Path]:
    root = Path(root)
    frag = fragment.lower()
    found: List[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = Path(dirpath) / fn
            try:
                rel = full.relative_to(root).as_posix().lower()
            except ValueError:
                rel = str(full).lower()
            if frag in rel:
                found.append(full)
                if len(found) >= limit:
                    return found
    return found
