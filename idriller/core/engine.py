from __future__ import annotations

from typing import Dict, List, Optional

from idriller.core.backup import BackupRoot
from idriller.core.models import ArtifactRecord
from idriller.parsers import all_parsers
from idriller.parsers.base import Parser


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
    backup_path: str,
    *,
    parser_ids: Optional[List[str]] = None,
    limit_per_parser: int = 50_000,
) -> List[ArtifactRecord]:
    backup = BackupRoot(backup_path)
    with backup.open_manifest() as manifest:
        parsers: List[Parser] = all_parsers()
        if parser_ids:
            wanted = set(parser_ids)
            parsers = [p for p in parsers if p.info.parser_id in wanted]
        results: List[ArtifactRecord] = []
        for p in parsers:
            try:
                results.extend(p.parse(backup, manifest, limit=limit_per_parser))
            except Exception:
                continue
        return results
