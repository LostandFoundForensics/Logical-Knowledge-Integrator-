"""Evidence hashing — read-only, streaming, never modifies the source."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def sha256_file(path: PathLike, *, chunk_size: int = 1024 * 1024) -> str:
    """
    Stream SHA-256 of a file. Evidence is only opened for reading.
    Large memory images are hashed in chunks to avoid loading whole file.
    """
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Not a file: {p}")
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
