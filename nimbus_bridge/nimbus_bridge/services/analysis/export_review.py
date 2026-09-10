from __future__ import annotations
import json
from pathlib import Path
from typing import List
from .models import GapFinding, ConflictFinding


def export_review_bundle(*, case_root: Path, gaps: List[GapFinding], conflicts: List[ConflictFinding]) -> Path:
    out_dir = case_root / "work" / "review"
    out_dir.mkdir(parents=True, exist_ok=True)
    from dataclasses import asdict
    bundle = {
        "read_only": True,
        "summary": {"gap_count": len(gaps), "conflict_count": len(conflicts)},
        "gaps": [asdict(g) for g in gaps],
        "conflicts": [asdict(c) for c in conflicts],
        "note": "Findings indicate data conditions only. No resolution or inference applied.",
    }
    out_path = out_dir / "cross_cloud_gaps_conflicts.json"
    out_path.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return out_path
