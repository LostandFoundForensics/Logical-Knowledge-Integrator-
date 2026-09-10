from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Observation:
    """One fact observed by a tool — not a conclusion."""
    obs_id: str
    source_tool: str
    artifact_type: str
    summary: str
    timestamp_unix_ms: Optional[int] = None
    timestamp_label: str = ""
    entities: List[str] = field(default_factory=list)  # phone numbers, emails, etc.
    payload: Dict[str, Any] = field(default_factory=dict)
    provenance_path: str = ""
    confidence: float = 0.9
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Entity:
    entity_id: str
    kind: str  # phone | email | name | other
    value: str
    first_seen_obs: str = ""
    obs_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
