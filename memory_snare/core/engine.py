from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from memory_snare.core.models import ArtifactHit
from memory_snare.parsers import all_parsers
from memory_snare.parsers.base import Parser


def list_parsers() -> List[Dict[str, str]]:
    return [
        {
            "id": p.info.parser_id,
            "label": p.info.label,
            "description": p.info.description,
        }
        for p in all_parsers()
    ]


def scan_dump(
    root: str | Path,
    *,
    parser_ids: Optional[List[str]] = None,
    limit_per_parser: int = 20_000,
) -> List[ArtifactHit]:
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(root)
    parsers: List[Parser] = all_parsers()
    if parser_ids:
        wanted = set(parser_ids)
        parsers = [p for p in parsers if p.info.parser_id in wanted]
    hits: List[ArtifactHit] = []
    for p in parsers:
        try:
            hits.extend(p.parse(root, limit=limit_per_parser))
        except Exception:
            continue
    return hits
