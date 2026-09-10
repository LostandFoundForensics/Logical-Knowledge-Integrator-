"""
LoKi shared SQLite helpers.

Doctrine:
  - Source evidence databases are ALWAYS opened read-only.
  - Never create -wal / -shm / journal files next to evidence.
  - Working/case databases we create ourselves may be read-write.

Usage for evidence:
    from loki_sqlite import open_evidence_ro
    with open_evidence_ro(path) as conn:
        ...

Usage for our own case/working DBs:
    from loki_sqlite import open_working_rw
    conn = open_working_rw(path)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


class EvidenceOpenError(OSError):
    """Raised when a source evidence DB cannot be opened read-only."""


def open_evidence_ro(
    db_path: PathLike,
    *,
    timeout_s: float = 5.0,
    check_same_thread: bool = False,
) -> sqlite3.Connection:
    """
    Open a source-evidence SQLite database in true read-only mode.

    Uses URI mode=ro so SQLite will not create journal/WAL/SHM files
    beside the evidence. Callers must treat the connection as read-only.
    """
    p = Path(db_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Evidence SQLite not found: {p}")
    if not p.is_file():
        raise EvidenceOpenError(f"Not a file: {p}")

    uri = f"file:{p.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(
            uri,
            uri=True,
            timeout=timeout_s,
            check_same_thread=check_same_thread,
        )
        conn.row_factory = sqlite3.Row
        # Defense in depth — even if something tries to write, fail fast.
        try:
            conn.execute("PRAGMA query_only = ON")
        except sqlite3.Error:
            pass
        # Force the connection to validate (URI opens can be lazy).
        conn.execute("SELECT 1")
        return conn
    except sqlite3.Error as e:
        raise EvidenceOpenError(
            f"Failed to open evidence SQLite read-only: {p} :: {e}"
        ) from e


def open_working_rw(
    db_path: PathLike,
    *,
    timeout_s: float = 30.0,
    check_same_thread: bool = False,
) -> sqlite3.Connection:
    """
    Open a LoKi-owned working/case database (read-write).

    Only use this for databases the platform creates (timelines, ledgers,
    normalized case DBs, findings stores). Never use for source evidence.
    """
    p = Path(db_path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(p),
        timeout=timeout_s,
        check_same_thread=check_same_thread,
    )
    conn.row_factory = sqlite3.Row
    return conn
