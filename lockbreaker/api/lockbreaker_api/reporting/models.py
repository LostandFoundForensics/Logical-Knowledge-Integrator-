from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class CourtReportInput:
    job_id: str
    case_id: str
    evidence_id: str
    evidence_filename: str
    evidence_sha256: str
    profile_name: str
    profile_description: str
    authorization_basis: str
    authorization_reference: str
    examiner: str
    organization: str
    started_at: datetime
    finished_at: datetime
    findings: List[Dict[str, Any]]
    artifacts: Dict[str, Any]
    signature_sha256: str
    signed_at: str
