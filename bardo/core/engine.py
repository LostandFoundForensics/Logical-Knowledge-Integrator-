from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from bardo.core.store import CaseStore
from bardo.ingest import generic as generic_mod
from bardo.ingest import jsonl_tools as jt


def list_sources() -> List[Dict[str, str]]:
    return [
        {"id": "android_excavator", "label": "Android Excavator", "description": "artifacts.jsonl from android_excavator extract"},
        {"id": "memory_snare", "label": "Memory Snare", "description": "artifacts.jsonl — accounts, browser, wifi"},
        {"id": "idriller", "label": "iDriller", "description": "artifacts.jsonl from idriller extract"},
        {"id": "recall_engine", "label": "Recall Engine", "description": "artifacts.jsonl — notes, Safari, calendar"},
        {"id": "pattern_harvester", "label": "Pattern Harvester", "description": "findings.jsonl — emails, phones, URLs, IPs"},
        {"id": "integrity_breaker", "label": "Integrity Breaker", "description": "findings.jsonl — IOC indicators"},
        {"id": "nimbus_bridge", "label": "Nimbus Bridge", "description": "artifacts.jsonl — Takeout contacts/activity"},
        {"id": "truthrelic", "label": "Truth Relic", "description": "inventory.jsonl — filesystem inventory"},
        {"id": "from_dir", "label": "Auto directory", "description": "Scan a loki case out/ folder for all known JSONL exports"},
        {"id": "generic", "label": "Generic JSONL", "description": "One JSON object per line with summary fields"},
    ]


def run_ingest(
    case_db: str | Path,
    *,
    excavator_jsonl: Optional[str] = None,
    idriller_jsonl: Optional[str] = None,
    memory_snare_jsonl: Optional[str] = None,
    recall_jsonl: Optional[str] = None,
    pattern_jsonl: Optional[str] = None,
    integrity_jsonl: Optional[str] = None,
    nimbus_jsonl: Optional[str] = None,
    truthrelic_jsonl: Optional[str] = None,
    generic_jsonl: Optional[str] = None,
    from_dir: Optional[str] = None,
    case_id: str = "",
) -> Dict[str, Any]:
    store = CaseStore(case_db)
    if case_id:
        store.set_meta("case_id", case_id)

    file_stats: List[Dict[str, Any]] = []

    mapping = [
        (excavator_jsonl, jt.ingest_excavator_jsonl),
        (idriller_jsonl, jt.ingest_idriller_jsonl),
        (memory_snare_jsonl, jt.ingest_memory_snare_jsonl),
        (recall_jsonl, jt.ingest_recall_engine_jsonl),
        (pattern_jsonl, jt.ingest_pattern_harvester_jsonl),
        (integrity_jsonl, jt.ingest_integrity_breaker_jsonl),
        (nimbus_jsonl, jt.ingest_nimbus_jsonl),
        (truthrelic_jsonl, jt.ingest_truthrelic_jsonl),
    ]
    for path, fn in mapping:
        if path:
            stats = fn(Path(path), store)
            file_stats.append(stats)

    if generic_jsonl:
        stats = generic_mod.ingest_generic_jsonl(Path(generic_jsonl), store)
        file_stats.append(stats)

    dir_stats = None
    if from_dir:
        dir_stats = jt.ingest_directory(Path(from_dir), store)
        file_stats.extend(dir_stats.get("files") or [])

    summary = store.summary()
    store.close()
    return {
        **summary,
        "file_stats": file_stats,
        "dir_stats": dir_stats,
    }
