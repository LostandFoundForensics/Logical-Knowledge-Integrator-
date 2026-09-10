"""
Witness Light — models.py
All data contracts for the platform.
Fix #1: now_iso() uses timezone-aware UTC (datetime.utcnow() is deprecated in 3.12+).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class Purpose(str, Enum):
    INTERNAL_REVIEW = "Internal review"
    REPORT_DRAFT = "Draft report language"
    COURT_READY = "Court-ready draft (conservative)"


class Intent(str, Enum):
    EXPLAIN_ARTIFACTS = "Explain selected artifacts"
    EXPLAIN_TIME_GAPS = "Explain time gaps"
    SUMMARIZE_ACTIVITY = "Summarize observed activity"
    DRAFT_REPORT_SECTION = "Draft report section"
    REWRITE_FOR_COURT = "Rewrite for court clarity"


class SentenceClass(str, Enum):
    OBSERVED = "Observed"
    CONTEXT = "Context"
    CONSISTENT_WITH = "Consistent With"
    LIMITATION = "Limitation"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class TruthloomHeader:
    dataset_id: str
    artifact_type: str
    os_version_tested: str
    app_version_tested: str
    extraction_method: str
    validation_date: str          # ISO date
    confidence_envelope: str      # High / Medium / Low
    known_failure_modes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    source_tool: str
    extraction_time_iso: str
    reference_path: str
    hash_value: str
    known_limitations: List[str] = field(default_factory=list)
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    schema_hash: Optional[str] = None
    truthloom_header: Optional[TruthloomHeader] = None


@dataclass
class Case:
    case_id: str
    case_name: str
    created_time_iso: str
    locked: bool


@dataclass
class DraftParagraph:
    sentence_class: SentenceClass
    text: str
    artifact_ids: List[str] = field(default_factory=list)
    truthloom_dataset_ids: List[str] = field(default_factory=list)
    confidence: str = "Inconclusive"  # High / Medium / Low / Inconclusive


@dataclass
class Draft:
    case_id: str
    purpose: Purpose
    intent: Intent
    created_time_iso: str
    disclaimer: str
    paragraphs: List[DraftParagraph]
    approved: bool = False
    approved_time_iso: Optional[str] = None
    approved_by: Optional[str] = None

    def as_text(self) -> str:
        lines = [self.disclaimer, ""]
        for i, p in enumerate(self.paragraphs, start=1):
            header = f"[{p.sentence_class.value}] (Confidence: {p.confidence})"
            lines.append(f"{i}. {header}")
            lines.append(p.text.strip())
            if p.artifact_ids:
                lines.append(f"   Sources: {', '.join(p.artifact_ids)}")
            if p.truthloom_dataset_ids:
                lines.append(f"   Validation: {', '.join(p.truthloom_dataset_ids)}")
            lines.append("")
        return "\n".join(lines).strip()


def now_iso() -> str:
    """
    FIX #1: timezone-aware UTC.
    datetime.utcnow() is deprecated in Python 3.12+ and returns a naive datetime.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
