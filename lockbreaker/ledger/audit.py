"""
Append-only audit ledger for LockBreaker actions.

Every survey, auth check, extract, and recovery attempt is recorded.
This is a working file we create — not source evidence.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def record(
        self,
        event: str,
        *,
        examiner: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "ts_epoch": int(time.time()),
            "event": event,
            "examiner": examiner,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
