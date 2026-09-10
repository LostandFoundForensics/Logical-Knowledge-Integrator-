from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from memory_snare.core.models import ArtifactHit


def write_jsonl(hits: List[ArtifactHit], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h.to_dict(), ensure_ascii=False) + "\n")
    return path


def write_summary_csv(hits: List[ArtifactHit], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["artifact_type", "summary", "source_path", "confidence"]
        )
        w.writeheader()
        for h in hits:
            w.writerow({
                "artifact_type": h.artifact_type,
                "summary": h.summary[:300],
                "source_path": h.source_path,
                "confidence": h.confidence,
            })
    return path
