"""Run selected parsers against a folder dump and collect artifacts."""
from __future__ import annotations

from typing import Dict, List, Optional

from android_excavator.core.models import ArtifactRecord
from android_excavator.core.source import FolderDump
from android_excavator.parsers import all_parsers
from android_excavator.parsers.base import Parser


def list_parsers() -> List[Dict[str, str]]:
    return [
        {
            "id": p.info.parser_id,
            "label": p.info.label,
            "description": p.info.description,
            "category": p.info.category,
        }
        for p in all_parsers()
    ]


def run_extract(
    root: str,
    *,
    parser_ids: Optional[List[str]] = None,
    limit_per_parser: int = 50_000,
) -> List[ArtifactRecord]:
    dump = FolderDump(root)
    dump.scan()
    parsers: List[Parser] = all_parsers()
    if parser_ids:
        wanted = set(parser_ids)
        parsers = [p for p in parsers if p.info.parser_id in wanted]
    results: List[ArtifactRecord] = []
    for p in parsers:
        try:
            results.extend(p.parse(dump, limit=limit_per_parser))
        except Exception:
            continue
    return results
