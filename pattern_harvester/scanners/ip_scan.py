from __future__ import annotations

import re
from typing import Iterable

from pattern_harvester.core.models import Finding
from pattern_harvester.scanners.base import Scanner, ScannerInfo

_IPV4 = re.compile(
    rb"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    rb"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)"
)


class IpScanner(Scanner):
    info = ScannerInfo(
        scanner_id="ip",
        label="IPv4 addresses",
        description="Finds dotted-quad IPv4 addresses.",
    )

    def scan(self, data: bytes, *, source_path: str, base_offset: int) -> Iterable[Finding]:
        for m in _IPV4.finditer(data):
            value = m.group(0).decode("ascii", errors="ignore")
            # skip obvious version-like 0.0.0.0 noise optionally kept with low confidence
            conf = 0.5 if value in ("0.0.0.0", "255.255.255.255") else 0.8
            yield Finding(
                pattern_type="ipv4",
                value=value,
                source_path=source_path,
                byte_offset=base_offset + m.start(),
                confidence=conf,
                scanner="ip@1.0",
                notes="IPv4 pattern match — may be version strings or false positives.",
            )
