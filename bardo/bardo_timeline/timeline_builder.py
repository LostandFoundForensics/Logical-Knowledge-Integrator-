from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..bardo_artifact_store.storage_sqlite import BardoStore
from ..bardo_core.schema import ArtifactType


@dataclass
class TimelineEntry:
    timestamp: datetime
    artifact_id: str
    artifact_type: str
    summary: str
    confidence: float
    source_tool: str
    entities: List[str] = field(default_factory=list)
    conflict_flag: bool = False
    conflict_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "summary": self.summary,
            "confidence": self.confidence,
            "source_tool": self.source_tool,
            "entities": self.entities,
            "conflict_flag": self.conflict_flag,
            "conflict_note": self.conflict_note,
        }


@dataclass
class Timeline:
    case_id: str
    entries: List[TimelineEntry] = field(default_factory=list)
    generated_at: str = ""
    total_conflicts: int = 0

    def sort(self) -> None:
        self.entries.sort(key=lambda e: e.timestamp)

    def filter_by_type(self, artifact_type: str) -> "Timeline":
        filtered = Timeline(case_id=self.case_id)
        filtered.entries = [e for e in self.entries if e.artifact_type == artifact_type]
        return filtered

    def filter_by_confidence(self, min_confidence: float) -> "Timeline":
        filtered = Timeline(case_id=self.case_id)
        filtered.entries = [e for e in self.entries if e.confidence >= min_confidence]
        return filtered

    def filter_by_range(self, start: datetime, end: datetime) -> "Timeline":
        filtered = Timeline(case_id=self.case_id)
        filtered.entries = [
            e for e in self.entries if start <= e.timestamp <= end
        ]
        return filtered

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "generated_at": self.generated_at,
            "total_entries": len(self.entries),
            "total_conflicts": self.total_conflicts,
            "entries": [e.to_dict() for e in self.entries],
        }


class TimelineBuilder:
    """
    Assembles a unified timeline from all artifacts in the Bardo store.
    Handles conflicts between tools with documented resolution.
    """

    def __init__(self, store: BardoStore):
        self.store = store

    def build(
        self,
        case_id: str,
        min_confidence: float = 0.0,
        artifact_types: Optional[List[str]] = None,
    ) -> Timeline:
        timeline = Timeline(case_id=case_id)
        conflicts = 0

        # Pull all artifact types or filtered subset
        types_to_query = (
            [ArtifactType(t) for t in artifact_types]
            if artifact_types
            else list(ArtifactType)
        )

        seen_ids = set()
        for atype in types_to_query:
            try:
                artifacts = self.store.query_artifacts_by_type(atype, limit=10000)
            except Exception:
                continue

            for art in artifacts:
                if art["artifact_id"] in seen_ids:
                    continue
                seen_ids.add(art["artifact_id"])

                if not art.get("best_time"):
                    continue

                if art["confidence"] < min_confidence:
                    continue

                try:
                    ts = datetime.fromisoformat(art["best_time"])
                except Exception:
                    continue

                # Extract entity labels for display
                import json
                entities_raw = art.get("entities_json", "[]")
                try:
                    entities = [
                        e.get("label") or e.get("entity_id", "")
                        for e in json.loads(entities_raw)
                    ]
                except Exception:
                    entities = []

                # Extract source tool from provenance
                prov_raw = art.get("provenance_json", "{}")
                try:
                    prov = json.loads(prov_raw)
                    source_tool = prov.get("acquisition_tool", "unknown")
                except Exception:
                    source_tool = "unknown"

                entry = TimelineEntry(
                    timestamp=ts,
                    artifact_id=art["artifact_id"],
                    artifact_type=art["artifact_type"],
                    summary=art.get("summary", ""),
                    confidence=art.get("confidence", 1.0),
                    source_tool=source_tool,
                    entities=[e for e in entities if e],
                )

                timeline.entries.append(entry)

        timeline.sort()
        timeline.total_conflicts = conflicts

        from datetime import timezone
        timeline.generated_at = datetime.now(timezone.utc).isoformat()
        return timeline
