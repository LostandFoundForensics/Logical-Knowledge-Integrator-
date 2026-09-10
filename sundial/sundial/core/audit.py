"""
Sundial — Audit Log + Hashing
Append-only session audit log (every reader action recorded) and SHA-256 helpers.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


class AuditLog:
    """
    Append-only JSONL audit log. Records APP_OPEN, CASE_OPEN, SCOPE_SET,
    BUILD_TIMELINE, VIEW_TIMELINE, OPEN_EVENT, INFERENCE_TOGGLE_SET,
    HIDE_INFERRED_EVENT, READING_MODE_SET, EXPORT, etc.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, action: str, details: Dict[str, Any] | None = None,
               actor: str = "user") -> None:
        entry = {
            "ts_utc": utc_now_iso(),
            "actor": actor,
            "action": action,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_all(self) -> list[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
