from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, *, max_bytes: int = 0, chunk: int = 1024 * 1024) -> str:
    """
    Hash a file read-only.
    max_bytes=0 → entire file; otherwise first max_bytes only (labeled by caller).
    """
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as f:
        while True:
            if max_bytes and total >= max_bytes:
                break
            to_read = chunk if not max_bytes else min(chunk, max_bytes - total)
            b = f.read(to_read)
            if not b:
                break
            h.update(b)
            total += len(b)
    return h.hexdigest()
