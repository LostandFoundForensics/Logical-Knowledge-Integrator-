from __future__ import annotations

import re
from typing import Iterable

from pattern_harvester.core.models import Finding
from pattern_harvester.scanners.base import Scanner, ScannerInfo

_URL = re.compile(
    rb"https?://[a-zA-Z0-9.\-]+(?::\d{2,5})?(?:/[^\s\"'<>]*)?",
    re.IGNORECASE,
)


class UrlScanner(Scanner):
    info = ScannerInfo(
        scanner_id="url",
        label="Web URLs",
        description="Finds http:// and https:// URLs.",
    )

    def scan(self, data: bytes, *, source_path: str, base_offset: int) -> Iterable[Finding]:
        for m in _URL.finditer(data):
            raw = m.group(0)
            # trim trailing punctuation often glued in text
            while raw and raw[-1:] in b".,;:)'\"]":
                raw = raw[:-1]
            try:
                value = raw.decode("ascii", errors="ignore")
            except Exception:
                continue
            if len(value) < 10:
                continue
            yield Finding(
                pattern_type="url",
                value=value[:500],
                source_path=source_path,
                byte_offset=base_offset + m.start(),
                confidence=0.9,
                scanner="url@1.0",
                notes="URL pattern match.",
            )
