"""
Witness Light — storage.py
Case and artifact loading, audit logging.
Fix #6: load_artifacts() now logs when Truthloom headers are missing or
        not specified, so examiners know which artifacts are unvalidated.
"""
from __future__ import annotations

import json
import os
from typing import List, Optional

from models import Case, ArtifactRef, TruthloomHeader, now_iso

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "audit")
AUDIT_LOG = os.path.join(AUDIT_DIR, "audit.log")


def ensure_dirs() -> None:
    os.makedirs(AUDIT_DIR, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "output"), exist_ok=True)


def audit(
    event: str,
    case_id: str,
    user: str,
    details: Optional[dict] = None,
) -> None:
    """Append-only audit log. Every action is recorded."""
    ensure_dirs()
    rec = {
        "time": now_iso(),
        "event": event,
        "case_id": case_id,
        "user": user,
        "details": details or {},
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_case(case_path: str) -> Case:
    with open(case_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Case(
        case_id=data["case_id"],
        case_name=data["case_name"],
        created_time_iso=data["created_time_iso"],
        locked=bool(data["locked"]),
    )


def _load_truthloom_header(path: str) -> TruthloomHeader:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return TruthloomHeader(
        dataset_id=d["dataset_id"],
        artifact_type=d["artifact_type"],
        os_version_tested=d["os_version_tested"],
        app_version_tested=d["app_version_tested"],
        extraction_method=d["extraction_method"],
        validation_date=d["validation_date"],
        confidence_envelope=d["confidence_envelope"],
        known_failure_modes=d.get("known_failure_modes", []),
    )


def load_artifacts(
    artifact_set_path: str,
    truthloom_dir: Optional[str] = None,
) -> List[ArtifactRef]:
    with open(artifact_set_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    artifacts: List[ArtifactRef] = []

    for a in data["artifacts"]:
        header: Optional[TruthloomHeader] = None

        if truthloom_dir:
            header_file = a.get("truthloom_header_file")
            if header_file:
                header_path = os.path.join(truthloom_dir, header_file)
                if os.path.exists(header_path):
                    header = _load_truthloom_header(header_path)
                else:
                    # FIX #6: log missing header file so examiner knows
                    audit(
                        "truthloom_header_missing",
                        a.get("artifact_id", "unknown"),
                        "system",
                        {
                            "artifact_id": a["artifact_id"],
                            "expected_path": header_path,
                            "note": (
                                "Truthloom header file specified but not found. "
                                "Artifact will be treated as unvalidated."
                            ),
                        },
                    )
            else:
                # FIX #6: log that no header was specified at all
                audit(
                    "truthloom_header_not_specified",
                    a.get("artifact_id", "unknown"),
                    "system",
                    {
                        "artifact_id": a["artifact_id"],
                        "note": (
                            "No Truthloom header file specified. "
                            "Artifact confidence will be Inconclusive."
                        ),
                    },
                )

        artifacts.append(
            ArtifactRef(
                artifact_id=a["artifact_id"],
                source_tool=a["source_tool"],
                extraction_time_iso=a["extraction_time_iso"],
                reference_path=a["reference_path"],
                hash_value=a["hash_value"],
                known_limitations=a.get("known_limitations", []),
                os_version=a.get("os_version"),
                app_version=a.get("app_version"),
                schema_hash=a.get("schema_hash"),
                truthloom_header=header,
            )
        )

    return artifacts
