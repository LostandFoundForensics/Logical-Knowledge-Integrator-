"""Observation models — no guilt fields, only what was seen."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Provenance:
    source_logical_path: str
    source_real_path: str
    source_sha256: str = ""
    acquired_via: str = "folder_dump"
    read_mode: str = "read_only"
    tool: str = "AndroidExcavator"
    tool_version: str = "1.0.0"


@dataclass
class Quality:
    evidence_strength: str = "observed_raw"  # observed_raw | observed_derived | best_effort
    confidence: float = 0.9
    flags: List[str] = field(default_factory=list)


@dataclass
class ArtifactRecord:
    artifact_type: str
    record: Dict[str, Any]
    provenance: Provenance
    quality: Quality = field(default_factory=Quality)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "record": self.record,
            "provenance": asdict(self.provenance),
            "quality": asdict(self.quality),
            "warnings": list(self.warnings),
        }
