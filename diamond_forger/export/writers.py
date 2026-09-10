from __future__ import annotations

import json
from pathlib import Path

from diamond_forger.core.models import JobResult


def write_result_json(result: JobResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return path
