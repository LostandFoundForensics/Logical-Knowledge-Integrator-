"""Write observations — never touch the evidence tree."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from android_excavator.core.models import ArtifactRecord


def write_jsonl(records: List[ArtifactRecord], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    return path


def write_summary_csv(records: List[ArtifactRecord], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["artifact_type", "summary", "source_path", "confidence"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            rec = r.record
            summary = (
                rec.get("body")
                or rec.get("url")
                or rec.get("display_name")
                or rec.get("number")
                or json.dumps(rec, ensure_ascii=False)[:120]
            )
            w.writerow({
                "artifact_type": r.artifact_type,
                "summary": str(summary)[:200] if summary is not None else "",
                "source_path": r.provenance.source_logical_path,
                "confidence": r.quality.confidence,
            })
    return path
