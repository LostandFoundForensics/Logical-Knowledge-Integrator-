from __future__ import annotations

import re
from typing import Iterable

from pattern_harvester.core.models import Finding
from pattern_harvester.scanners.base import Scanner, ScannerInfo

_E164 = re.compile(rb"\+[1-9]\d{6,14}(?!\d)")
_NANP = re.compile(
    rb"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)"
)


class PhoneScanner(Scanner):
    info = ScannerInfo(
        scanner_id="phone",
        label="Phone numbers",
        description="Finds E.164 and common North-American style numbers.",
    )

    def scan(self, data: bytes, *, source_path: str, base_offset: int) -> Iterable[Finding]:
        seen = set()
        for m in _E164.finditer(data):
            val = m.group(0).decode("ascii", errors="ignore")
            key = (base_offset + m.start(), val)
            if key in seen:
                continue
            seen.add(key)
            yield Finding(
                pattern_type="phone",
                value=val,
                source_path=source_path,
                byte_offset=base_offset + m.start(),
                confidence=0.88,
                scanner="phone@1.0",
                notes="E.164-like. Not validated as assigned.",
            )
        for m in _NANP.finditer(data):
            val = m.group(0).decode("ascii", errors="ignore")
            key = (base_offset + m.start(), val)
            if key in seen:
                continue
            seen.add(key)
            yield Finding(
                pattern_type="phone",
                value=val,
                source_path=source_path,
                byte_offset=base_offset + m.start(),
                confidence=0.7,
                scanner="phone@1.0",
                notes="NANP-like pattern. Higher false-positive rate.",
            )
