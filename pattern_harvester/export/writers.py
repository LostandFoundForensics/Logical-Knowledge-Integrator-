from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import List

from pattern_harvester.core.models import Finding


def write_jsonl(findings: List[Finding], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in findings:
            f.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
    return path


def write_summary_csv(findings: List[Finding], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["pattern_type", "value", "source_path", "byte_offset", "confidence"],
        )
        w.writeheader()
        for item in findings:
            w.writerow({
                "pattern_type": item.pattern_type,
                "value": item.value[:300],
                "source_path": item.source_path,
                "byte_offset": item.byte_offset,
                "confidence": item.confidence,
            })
    return path


def counts_by_type(findings: List[Finding]) -> dict:
    return dict(Counter(f.pattern_type for f in findings))
