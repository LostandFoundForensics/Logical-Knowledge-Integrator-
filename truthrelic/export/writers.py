from __future__ import annotations

import json
from pathlib import Path
from typing import List

from truthrelic.core.models import FileEntry, ImageProbe


def write_inventory_jsonl(entries: List[FileEntry], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
    return path


def write_probe_json(probe: ImageProbe, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(probe.to_dict(), indent=2), encoding="utf-8")
    return path
