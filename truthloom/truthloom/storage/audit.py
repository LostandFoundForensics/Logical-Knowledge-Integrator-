from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _utc_now(): return datetime.now(timezone.utc).isoformat()
def _sha256(text): return hashlib.sha256(text.encode("utf-8")).hexdigest()
def _canonical(entry): return json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",",":"))

class AuditLog:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self):
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return "GENESIS"
        try:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines):
                line = line.strip()
                if line:
                    return json.loads(line).get("entry_hash", "GENESIS")
        except Exception:
            pass
        return "GENESIS"

    def append(self, action: str, details: Optional[Dict[str, Any]] = None) -> str:
        prev_hash = self._last_hash()
        entry = {"timestamp_utc": _utc_now(), "action": action, "details": details or {}, "prev_hash": prev_hash}
        entry_hash = _sha256(_canonical(entry))
        entry["entry_hash"] = entry_hash
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry_hash

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []
        entries = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try: entries.append(json.loads(line))
                except json.JSONDecodeError: pass
        return entries

    def verify_chain(self) -> Tuple[bool, List[str]]:
        entries = self.read_all()
        errors: List[str] = []
        prev_hash = "GENESIS"
        for i, entry in enumerate(entries):
            stored_prev = entry.get("prev_hash", "")
            stored_hash = entry.get("entry_hash", "")
            if stored_prev != prev_hash:
                errors.append(f"Entry {i} ({entry.get('action','?')}): prev_hash mismatch")
            check_entry = {k: v for k, v in entry.items() if k != "entry_hash"}
            recomputed = _sha256(_canonical(check_entry))
            if recomputed != stored_hash:
                errors.append(f"Entry {i} ({entry.get('action','?')}): entry_hash mismatch - log was modified")
            prev_hash = stored_hash
        return (len(errors) == 0, errors)
