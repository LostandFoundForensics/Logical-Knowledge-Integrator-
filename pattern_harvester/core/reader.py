"""Read evidence files in overlapping chunks — never write to them."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple


def iter_chunks(
    path: Path,
    *,
    chunk_size: int = 2 * 1024 * 1024,
    overlap: int = 256,
    max_bytes: int = 0,
) -> Iterator[Tuple[bytes, int]]:
    """
    Yield (chunk_bytes, absolute_offset).
    max_bytes=0 means whole file.
    """
    path = Path(path)
    size = path.stat().st_size
    limit = size if max_bytes <= 0 else min(size, max_bytes)
    with path.open("rb") as f:
        offset = 0
        while offset < limit:
            to_read = min(chunk_size, limit - offset)
            f.seek(offset)
            data = f.read(to_read)
            if not data:
                break
            yield data, offset
            if offset + to_read >= limit:
                break
            offset += max(1, chunk_size - overlap)


def iter_files(root: Path, *, max_files: int = 50_000) -> Iterator[Path]:
    root = Path(root)
    if root.is_file():
        yield root
        return
    n = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # Skip obvious noise
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mkv", ".avi"}:
            continue
        yield p
        n += 1
        if n >= max_files:
            break
