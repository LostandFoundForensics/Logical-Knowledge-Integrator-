from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    PERSON      = "PERSON"
    DEVICE      = "DEVICE"
    ACCOUNT     = "ACCOUNT"
    APPLICATION = "APPLICATION"
    SERVICE     = "SERVICE"
    LOCATION    = "LOCATION"


class ArtifactType(str, Enum):
    MESSAGE        = "MESSAGE"
    CALL           = "CALL"
    MEDIA          = "MEDIA"
    LOCATION_POINT = "LOCATION_POINT"
    WEB_ACTIVITY   = "WEB_ACTIVITY"
    APP_ACTIVITY   = "APP_ACTIVITY"
    SYSTEM_EVENT   = "SYSTEM_EVENT"
    FILE_METADATA  = "FILE_METADATA"
    AUTH_EVENT     = "AUTH_EVENT"
    INSTALL_EVENT  = "INSTALL_EVENT"
    NETWORK_EVENT  = "NETWORK_EVENT"
    CLOUD_EVENT    = "CLOUD_EVENT"
    UNKNOWN        = "UNKNOWN"


class EventType(str, Enum):
    COMMUNICATION    = "COMMUNICATION"
    MOVEMENT         = "MOVEMENT"
    AUTHENTICATION   = "AUTHENTICATION"
    CREATION         = "CREATION"
    MODIFICATION     = "MODIFICATION"
    DELETION         = "DELETION"
    POWER_STATE      = "POWER_STATE"
    INSTALLATION     = "INSTALLATION"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    UNKNOWN          = "UNKNOWN"


class RelationshipType(str, Enum):
    OWNS             = "OWNS"
    USED_BY          = "USED_BY"
    COMMUNICATED_WITH = "COMMUNICATED_WITH"
    LOCATED_AT       = "LOCATED_AT"
    INSTALLED_ON     = "INSTALLED_ON"
    AUTHENTICATED_AS = "AUTHENTICATED_AS"
    GENERATED        = "GENERATED"


class TimeSource(str, Enum):
    FILESYSTEM = "FILESYSTEM"
    APP_LOG    = "APP_LOG"
    SYSTEM_LOG = "SYSTEM_LOG"
    CLOUD_LOG  = "CLOUD_LOG"
    INFERRED   = "INFERRED"


# ── Supporting types ──────────────────────────────────────────────────────────

@dataclass
class TimeRange:
    earliest: datetime
    latest:   datetime
    confidence: float = 1.0

    def __post_init__(self):
        if self.earliest > self.latest:
            raise ValueError(
                f"TimeRange.earliest ({self.earliest}) must be <= latest ({self.latest})"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0–1.0, got {self.confidence}")

    @property
    def duration_seconds(self) -> float:
        return (self.latest - self.earliest).total_seconds()

    def overlaps(self, other: "TimeRange") -> bool:
        return self.earliest <= other.latest and other.earliest <= self.latest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "earliest": self.earliest.isoformat(),
            "latest": self.latest.isoformat(),
            "confidence": self.confidence,
        }


@dataclass
class TimeAssertion:
    """
    A single timestamped claim about when something occurred.
    Carries its own confidence and source so downstream consumers
    can weigh FILESYSTEM timestamps differently from INFERRED ones.
    """
    source:     TimeSource
    confidence: float
    timestamp:  Optional[datetime] = None
    time_range: Optional[TimeRange] = None
    timezone:   Optional[str] = None
    notes:      Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None and self.time_range is None:
            raise ValueError("TimeAssertion requires at least one of: timestamp, time_range")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0–1.0, got {self.confidence}")

    @property
    def best_datetime(self) -> Optional[datetime]:
        """Returns the most precise datetime available."""
        if self.timestamp:
            return self.timestamp
        if self.time_range:
            return self.time_range.earliest
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "time_range": self.time_range.to_dict() if self.time_range else None,
            "timezone": self.timezone,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EntityRef:
    entity_id: str
    entity_type: EntityType
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "label": self.label,
        }


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    artifact_type: ArtifactType
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "summary": self.summary,
        }


@dataclass
class Provenance:
    acquisition_tool:      str
    tool_version:          str
    source_file:           str
    source_hash:           str
    ingest_time:           datetime
    transformation_steps:  List[str] = field(default_factory=list)
    analyst_actions:       List[str] = field(default_factory=list)
    provenance_id:         str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_transform(self, step: str) -> None:
        self.transformation_steps.append(step)

    def add_analyst_action(self, action: str) -> None:
        self.analyst_actions.append(action)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "acquisition_tool": self.acquisition_tool,
            "tool_version": self.tool_version,
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "ingest_time": self.ingest_time.isoformat(),
            "transformation_steps": self.transformation_steps,
            "analyst_actions": self.analyst_actions,
        }


# ── Core entities ─────────────────────────────────────────────────────────────

@dataclass
class Entity:
    entity_type:  EntityType
    labels:       List[str] = field(default_factory=list)
    attributes:   Dict[str, Any] = field(default_factory=dict)
    first_seen:   Optional[TimeRange] = None
    last_seen:    Optional[TimeRange] = None
    confidence:   float = 1.0
    entity_id:    str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_ref(self) -> EntityRef:
        label = self.labels[0] if self.labels else None
        return EntityRef(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            label=label,
        )

    def merge_attributes(self, other: "Entity") -> None:
        """Merge another entity's attributes into this one (for entity resolution)."""
        for k, v in other.attributes.items():
            if k not in self.attributes:
                self.attributes[k] = v
        for label in other.labels:
            if label not in self.labels:
                self.labels.append(label)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "labels": self.labels,
            "attributes": self.attributes,
            "first_seen": self.first_seen.to_dict() if self.first_seen else None,
            "last_seen": self.last_seen.to_dict() if self.last_seen else None,
            "confidence": self.confidence,
        }


@dataclass
class Artifact:
    artifact_type:     ArtifactType
    summary:           str
    payload:           Dict[str, Any]
    source_provenance: Provenance
    subtype:           str = ""
    related_entities:  List[EntityRef] = field(default_factory=list)
    observed_times:    List[TimeAssertion] = field(default_factory=list)
    confidence:        float = 1.0
    artifact_id:       str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def best_time(self) -> Optional[datetime]:
        """Returns the highest-confidence timestamp across all assertions."""
        if not self.observed_times:
            return None
        best = max(self.observed_times, key=lambda t: t.confidence)
        return best.best_datetime

    def to_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.artifact_id,
            artifact_type=self.artifact_type,
            summary=self.summary[:120],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "subtype": self.subtype,
            "summary": self.summary,
            "payload": self.payload,
            "related_entities": [e.to_dict() for e in self.related_entities],
            "observed_times": [t.to_dict() for t in self.observed_times],
            "source_provenance": self.source_provenance.to_dict(),
            "confidence": self.confidence,
        }


@dataclass
class Event:
    event_type:           EventType
    description:          str
    time_window:          TimeRange
    involved_entities:    List[EntityRef] = field(default_factory=list)
    supporting_artifacts: List[ArtifactRef] = field(default_factory=list)
    location:             Optional[EntityRef] = None
    confidence:           float = 1.0
    event_id:             str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "description": self.description,
            "involved_entities": [e.to_dict() for e in self.involved_entities],
            "supporting_artifacts": [a.to_dict() for a in self.supporting_artifacts],
            "time_window": self.time_window.to_dict(),
            "location": self.location.to_dict() if self.location else None,
            "confidence": self.confidence,
        }


@dataclass
class Relationship:
    from_entity:          EntityRef
    to_entity:            EntityRef
    relationship_type:    RelationshipType
    supporting_artifacts: List[ArtifactRef] = field(default_factory=list)
    confidence:           float = 1.0
    # ADDED: temporal dimension — when did this relationship exist?
    time_window:          Optional[TimeRange] = None
    notes:                str = ""
    relationship_id:      str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "from": self.from_entity.to_dict(),
            "to": self.to_entity.to_dict(),
            "relationship_type": self.relationship_type.value,
            "supporting_artifacts": [a.to_dict() for a in self.supporting_artifacts],
            "confidence": self.confidence,
            "time_window": self.time_window.to_dict() if self.time_window else None,
            "notes": self.notes,
        }
