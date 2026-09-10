from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class IntakeReport:
    path: str
    kind: str  # ios_backup | android_ab | unknown | folder
    encrypted: bool | None
    summary: str
    findings: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
