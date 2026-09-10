from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class Finding:
    pattern_type: str
    value: str
    source_path: str
    byte_offset: int
    confidence: float
    scanner: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
