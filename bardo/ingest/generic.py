"""Generic JSONL: one observation per line with flexible keys."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from bardo.core.models import Observation
from bardo.core.store import CaseStore


def ingest_generic_jsonl(
    path: Path,
    store: CaseStore,
    *,
    source_tool: str = "generic",
) -> Dict[str, int]:
    path = Path(path)
    added = 0
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            summary = str(
                obj.get("summary")
                or obj.get("text")
                or obj.get("body")
                or obj.get("message")
                or f"row-{i}"
            )[:200]
            raw = f"{source_tool}|{i}|{summary}|{json.dumps(obj, sort_keys=True, default=str)}"
            oid = hashlib.sha256(raw.encode()).hexdigest()[:24]
            ts = obj.get("timestamp_unix_ms") or obj.get("ts_ms")
            try:
                ts_i = int(ts) if ts is not None else None
            except Exception:
                ts_i = None
            obs = Observation(
                obs_id=oid,
                source_tool=source_tool,
                artifact_type=str(obj.get("artifact_type") or obj.get("type") or "generic"),
                summary=summary,
                timestamp_unix_ms=ts_i,
                timestamp_label=str(obj.get("date_iso") or ""),
                entities=list(obj.get("entities") or []),
                payload=obj,
                provenance_path=str(obj.get("source") or ""),
                confidence=float(obj.get("confidence") or 0.8),
                flags=list(obj.get("flags") or []),
            )
            store.upsert_observation(obs)
            added += 1
    return {"added": added, "tool": source_tool}
