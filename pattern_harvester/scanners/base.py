from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from pattern_harvester.core.models import Finding


@dataclass(frozen=True)
class ScannerInfo:
    scanner_id: str
    label: str
    description: str


class Scanner(ABC):
    info: ScannerInfo

    @abstractmethod
    def scan(self, data: bytes, *, source_path: str, base_offset: int) -> Iterable[Finding]:
        ...
