from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

from pattern_harvester.core.models import Finding
from pattern_harvester.core.reader import iter_chunks, iter_files
from pattern_harvester.scanners import all_scanners
from pattern_harvester.scanners.base import Scanner


def list_scanners() -> List[Dict[str, str]]:
    return [
        {
            "id": s.info.scanner_id,
            "label": s.info.label,
            "description": s.info.description,
        }
        for s in all_scanners()
    ]


def scan_path(
    root: str | Path,
    *,
    scanner_ids: Optional[List[str]] = None,
    max_files: int = 10_000,
    max_file_bytes: int = 32 * 1024 * 1024,
    max_findings: int = 100_000,
) -> List[Finding]:
    """
    Scan a file or directory tree read-only.
    Dedupes identical (type, value, path) triples.
    """
    root = Path(root)
    scanners: List[Scanner] = all_scanners()
    if scanner_ids:
        wanted = set(scanner_ids)
        scanners = [s for s in scanners if s.info.scanner_id in wanted]

    findings: List[Finding] = []
    seen: Set[tuple] = set()

    for fpath in iter_files(root, max_files=max_files):
        try:
            rel = str(fpath)
            for data, offset in iter_chunks(fpath, max_bytes=max_file_bytes):
                for sc in scanners:
                    for finding in sc.scan(data, source_path=rel, base_offset=offset):
                        key = (finding.pattern_type, finding.value, finding.source_path)
                        if key in seen:
                            continue
                        seen.add(key)
                        findings.append(finding)
                        if len(findings) >= max_findings:
                            return findings
        except (OSError, PermissionError):
            continue
    return findings
