from __future__ import annotations

import json
from pathlib import Path

from bardo.core.store import CaseStore


def export_timeline_json(store: CaseStore, path: Path, *, limit: int = 10000) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "tool": "BardoEngine",
        "version": "1.0.0",
        "case_id": store.get_meta("case_id"),
        "events": store.timeline(limit=limit),
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_summary_json(store: CaseStore, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "tool": "BardoEngine",
        "version": "1.0.0",
        "summary": store.summary(),
        "top_entities": store.list_entities(limit=50),
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
