from __future__ import annotations

import json
from pathlib import Path

from echoreader.core.models import IntakeReport


def write_report_json(report: IntakeReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
