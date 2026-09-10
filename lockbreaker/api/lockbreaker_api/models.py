from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime

AttackProfile = Literal[
    "ios_encrypted_backup",
    "ios_keychain",
    "android_encrypted_backup",
    "android_pin_4digit",
    "android_pin_6digit",
    "android_pattern",
    "app_sqlite_encrypted",
    "generic_hash_wordlist_rules",
    "generic_hash_mask",
]

AuthBasis = Literal["consent", "warrant", "court_order", "owner_recovery", "other"]

class Authorization(BaseModel):
    basis: AuthBasis
    reference_id: str = Field(..., description="Case/warrant/court-order reference ID")
    notes: Optional[str] = None

class EvidenceRef(BaseModel):
    case_id: str
    evidence_id: str
    filename: str
    sha256: str
    evidence_kind: Optional[str] = None   # ios_backup | android_backup | hashfile | etc.
    storage_uri: Optional[str] = None

class WordlistRef(BaseModel):
    name: str
    sha256: str

class ExaminerInputs(BaseModel):
    owner_name: Optional[str] = None
    backup_path_relative: Optional[str] = "."
    hash_file_relative: Optional[str] = "derived/lock_hash.txt"
    wordlist_id: Optional[str] = None
    max_runtime_minutes: Optional[int] = 1440
    pattern_complexity: Optional[str] = None
    known_pin_length: Optional[str] = None

class JobRequest(BaseModel):
    submitted_by: str
    evidence: EvidenceRef
    authorization: Authorization
    attack_profile: AttackProfile
    examiner_inputs: Optional[ExaminerInputs] = None
    format_hint: Optional[str] = None
    wordlist: Optional[WordlistRef] = None
    rules: Optional[List[str]] = None
    max_runtime_minutes: int = Field(default=1440, gt=0, le=10080)  # max 1 week
    redaction_mode: str = "court_safe"

class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed", "rejected", "canceled"]
    progress: float = 0.0
    message: Optional[str] = None
    updated_at: datetime
    stage: Optional[str] = None

class Finding(BaseModel):
    item: str
    value: str
    method: str
    complexity: Optional[str] = None
    pattern_class: Optional[str] = None
    court_note: Optional[str] = None
    recovered_at: Optional[str] = None

class LockBreakerResult(BaseModel):
    job_id: str
    case_id: str
    evidence_id: str
    profile_id: str
    worker_version: str = "lockbreaker-worker-1.0"
    started_at: str
    finished_at: str
    findings: List[Dict[str, Any]] = []
    artifacts: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}
    audit: Dict[str, Any] = {}
    court_explanation: Optional[str] = None
