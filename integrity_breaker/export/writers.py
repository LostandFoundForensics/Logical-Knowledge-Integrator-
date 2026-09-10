from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from integrity_breaker.core.models import Finding


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
            fieldnames=["severity", "rule_id", "title", "source_path", "matched", "confidence"],
        )
        w.writeheader()
        for item in findings:
            w.writerow({
                "severity": item.severity,
                "rule_id": item.rule_id,
                "title": item.title,
                "source_path": item.source_path,
                "matched": item.matched[:120],
                "confidence": item.confidence,
            })
    return path
