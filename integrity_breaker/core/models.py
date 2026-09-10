from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class Finding:
    rule_id: str
    title: str
    severity: str  # low | medium | high | info
    match_on: str  # path | content
    matched: str
    source_path: str
    snippet: str = ""
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
