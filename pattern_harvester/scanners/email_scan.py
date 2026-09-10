from __future__ import annotations

import re
from typing import Iterable

from pattern_harvester.core.models import Finding
from pattern_harvester.scanners.base import Scanner, ScannerInfo

_EMAIL = re.compile(
    rb"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,24}"
)


class EmailScanner(Scanner):
    info = ScannerInfo(
        scanner_id="email",
        label="Email addresses",
        description="Finds strings that look like email addresses.",
    )

    def scan(self, data: bytes, *, source_path: str, base_offset: int) -> Iterable[Finding]:
        for m in _EMAIL.finditer(data):
            try:
                value = m.group(0).decode("ascii", errors="ignore")
            except Exception:
                continue
            if value.count("@") != 1:
                continue
            yield Finding(
                pattern_type="email",
                value=value,
                source_path=source_path,
                byte_offset=base_offset + m.start(),
                confidence=0.85,
                scanner="email@1.0",
                notes="Pattern match only — not verified as a live mailbox.",
            )
