"""
Timeline event model — original ChronoChain schema.

Every event is an observation with a time, a category, and provenance.
No inferred “guilt” fields — conclusions stay with the human.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Timestamp:
    epoch_ms: int
    ts_type: str = "EXACT"          # EXACT | APPROXIMATE | UNKNOWN
    confidence: float = 1.0         # 0.0–1.0
    original_value: str = ""
    original_format: str = ""       # e.g. apple_absolute, unix_s, iso8601
    timezone_hint: str = "UTC"
    notes: str = ""


@dataclass
class Provenance:
    evidence_id: str
    source_path: str
    extractor: str
    recipe: str = ""
    artifact_ref: str = ""
    hash_chain: List[str] = field(default_factory=list)


@dataclass
class TimelineEvent:
    event_id: str
    ts: Timestamp
    category: str                   # COMMS | WEB | FILE | SYSTEM | LOCATION | OTHER
    title: str
    description: str = ""
    actors: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    provenance: Provenance = field(
        default_factory=lambda: Provenance(evidence_id="", source_path="", extractor="")
    )
    observed: bool = True           # True = directly observed; False = synthetic notice

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "epoch_ms": self.ts.epoch_ms,
            "ts_type": self.ts.ts_type,
            "ts_confidence": self.ts.confidence,
            "ts_original_value": self.ts.original_value,
            "ts_original_format": self.ts.original_format,
            "ts_timezone_hint": self.ts.timezone_hint,
            "ts_notes": self.ts.notes,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "actors": list(self.actors),
            "tags": list(self.tags),
            "attributes": dict(self.attributes),
            "evidence_id": self.provenance.evidence_id,
            "source_path": self.provenance.source_path,
            "extractor": self.provenance.extractor,
            "recipe": self.provenance.recipe,
            "artifact_ref": self.provenance.artifact_ref,
            "hash_chain": list(self.provenance.hash_chain),
            "observed": self.observed,
        }
