from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_bardo_timeline(path: Path) -> List[Dict[str, Any]]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "events" in data:
        return list(data["events"])
    if isinstance(data, list):
        return data
    raise ValueError("Unrecognized Bardo timeline format")
