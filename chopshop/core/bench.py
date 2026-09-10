"""Create a standard Chop Shop bench (case workspace)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

from chopshop.core.stations import list_stations


BENCH_DIRS = (
    "evidence_links",   # operator places path notes / copies references
    "out",              # tool outputs
    "notes",            # free-form examiner notes
    "exports",          # court / handoff packages
    "logs",             # bench audit
)


def create_bench(
    path: str | Path,
    *,
    case_name: str = "",
    examiner: str = "",
) -> Dict:
    root = Path(path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for d in BENCH_DIRS:
        (root / d).mkdir(exist_ok=True)

    meta = {
        "tool": "ChopShop",
        "version": "1.0.0",
        "case_name": case_name or root.name,
        "examiner": examiner,
        "created_epoch": time.time(),
        "bench_root": str(root),
        "stations": list_stations(),
        "rules": [
            "Do not write into original evidence paths.",
            "Put tool outputs under out/.",
            "Record authority notes under notes/.",
        ],
    }
    (root / "bench.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (root / "notes" / "README.txt").write_text(
        "Examiner notes go here. Authority / warrant references recommended.\n",
        encoding="utf-8",
    )
    (root / "logs" / "bench.jsonl").write_text(
        json.dumps({"event": "bench_created", "case_name": meta["case_name"]}) + "\n",
        encoding="utf-8",
    )
    return meta


def list_stations() -> List[Dict[str, object]]:
    from chopshop.core.stations import list_stations as _ls

    return _ls()
