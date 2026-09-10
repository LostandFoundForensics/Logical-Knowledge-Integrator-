from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from .enums import ArtifactType, Confidence, CopyPolicy, DatasetMode, IntakeState, SourceMethod, SourceType, TruthState

def _new_id(): return str(uuid.uuid4())
def _utc_now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class Participant:
    id: str
    label: str

@dataclass
class Timestamp:
    value: str
    timezone: str

@dataclass
class Assertion:
    asserted_by: Optional[str] = None
    asserted_utc: Optional[str] = None
    approved_by: Optional[str] = None
    approved_utc: Optional[str] = None

@dataclass
class Source:
    method: SourceMethod = SourceMethod.MANUAL_ENTRY
    reference: Optional[str] = None

@dataclass
class TruthRecord:
    record_id: str
    state: TruthState
    artifact_type: ArtifactType
    timestamp: Timestamp
    participants: List[Participant]
    confidence: Confidence
    source: Source
    assertion: Assertion
    direction: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def new(cls, artifact_type, timestamp, participants, confidence=Confidence.CERTAIN,
            source=None, direction=None, content=None, attachments=None, notes="", asserted_by=None):
        return cls(
            record_id=_new_id(), state=TruthState.DRAFT_TRUTH,
            artifact_type=artifact_type, timestamp=timestamp, participants=participants,
            confidence=confidence, source=source or Source(),
            assertion=Assertion(asserted_by=asserted_by, asserted_utc=_utc_now() if asserted_by else None),
            direction=direction, content=content, attachments=attachments or [], notes=notes,
        )

    def approve(self, approved_by: str):
        if self.state != TruthState.DRAFT_TRUTH:
            raise ValueError(f"Cannot approve record in state {self.state!r}")
        self.state = TruthState.OBSERVED_TRUTH
        self.assertion.approved_by = approved_by
        self.assertion.approved_utc = _utc_now()

    def revoke(self):
        if self.state != TruthState.OBSERVED_TRUTH:
            raise ValueError(f"Cannot revoke record in state {self.state!r}")
        self.state = TruthState.DRAFT_TRUTH
        self.assertion.approved_by = None
        self.assertion.approved_utc = None

@dataclass
class IntakeHash:
    sha256: Optional[str] = None

@dataclass
class IntakeRecord:
    intake_id: str
    state: IntakeState
    source_type: SourceType
    source_path: str
    copy_policy: CopyPolicy
    dataset_path: Optional[str]
    bytes: Optional[int]
    hash: IntakeHash
    added_utc: str
    copied_utc: Optional[str] = None
    hashed_utc: Optional[str] = None
    excluded_utc: Optional[str] = None
    notes: str = ""

    @classmethod
    def new(cls, source_path, source_type=SourceType.GENERIC_FILES, copy_policy=CopyPolicy.COPY_PRESERVE_TREE, notes=""):
        return cls(
            intake_id=f"in_{uuid.uuid4().hex[:8]}", state=IntakeState.STAGED,
            source_type=source_type, source_path=source_path, copy_policy=copy_policy,
            dataset_path=None, bytes=None, hash=IntakeHash(), added_utc=_utc_now(), notes=notes,
        )

@dataclass
class Dataset:
    dataset_id: str
    name: str
    created_utc: str
    created_by: str
    loki_schema_version: str = "1.0"
    truthloom_version: str = "0.1"
    scope: List[str] = field(default_factory=list)
    artifact_families: List[str] = field(default_factory=list)
    status: str = "draft"
    mode: DatasetMode = DatasetMode.NORMAL

    @classmethod
    def new(cls, name, created_by, scope=None, artifact_families=None):
        return cls(dataset_id=_new_id(), name=name, created_utc=_utc_now(), created_by=created_by,
                   scope=scope or [], artifact_families=artifact_families or [])
