from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class ArtifactHit:
    artifact_type: str
    summary: str
    record: Dict[str, Any]
    source_path: str
    domain: str = ""
    file_id: str = ""
    confidence: float = 0.85
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
