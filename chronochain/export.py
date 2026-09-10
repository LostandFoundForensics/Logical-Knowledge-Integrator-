"""
Export timeline for humans — CSV and JSONL.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from chronochain.core.schema import TimelineEvent
from chronochain.core.normalize import epoch_ms_to_iso


def export_jsonl(events: List[TimelineEvent], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
    return path


def export_csv(events: List[TimelineEvent], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "when_utc", "category", "title", "description",
        "actors", "source_path", "extractor", "event_id",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for ev in events:
            w.writerow({
                "when_utc": epoch_ms_to_iso(ev.ts.epoch_ms),
                "category": ev.category,
                "title": ev.title,
                "description": ev.description,
                "actors": "; ".join(ev.actors),
                "source_path": ev.provenance.source_path,
                "extractor": ev.provenance.extractor,
                "event_id": ev.event_id,
            })
    return path
