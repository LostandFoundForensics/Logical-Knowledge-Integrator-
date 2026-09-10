from __future__ import annotations

import json
from pathlib import Path

from witness_light.core.models import DraftReport


def write_report_txt(report: DraftReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_text(), encoding="utf-8")
    return path


def write_report_json(report: DraftReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
