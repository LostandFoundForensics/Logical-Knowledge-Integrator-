"""
Update Trap — core/claim_pack_importer.py
Reads an Update Trap claim pack folder and returns an UpdateEvent + raw
payload. LoKi should store the UpdateEvent and attach the raw files as
immutable evidence.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class UpdateEvent:
    event_id: str
    created_utc: str
    tool: str
    baseline_label: str
    new_label: str
    source_profile: str
    targets: List[str]
    structured_key_diff: List[str]
    summary: dict
    artifacts: dict  # file names -> presence booleans


class ClaimPackImporter:
    """
    Reads an Update Trap claim pack folder and returns an UpdateEvent +
    raw payload. LoKi should store the UpdateEvent and attach the raw
    files as immutable evidence.
    """

    REQUIRED = ["claim_pack.json", "diff_report.json", "parser_rules.json"]

    def load_claim_pack(self, claim_pack_dir: str) -> Dict[str, Any]:
        for fn in self.REQUIRED:
            p = os.path.join(claim_pack_dir, fn)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Missing required file: {fn}")

        def read(name: str) -> Optional[dict]:
            p = os.path.join(claim_pack_dir, name)
            if not os.path.exists(p):
                return None
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)

        claim = read("claim_pack.json") or {}
        diff = read("diff_report.json") or {}
        rules = read("parser_rules.json") or {}
        breakage = read("parser_breakage_assessment.json")
        advisory = read("signature_advisory.json")

        return {
            "claim_pack": claim,
            "diff_report": diff,
            "parser_rules": rules,
            "breakage": breakage,
            "advisory": advisory,
        }

    def to_update_event(self, payload: Dict[str, Any]) -> UpdateEvent:
        claim = payload["claim_pack"]
        diff = payload["diff_report"]

        # export.py now always writes scope into claim_pack.json directly
        # (Phase 1/2's exporter never wrote it — this is one of the fixes
        # applied when this package was merged), so this reads from there
        # first and falls back to "unknown" only for claim packs produced
        # by an older, pre-fix exporter.
        scope = claim.get("scope") or {}
        source_profile = scope.get("source_profile", "unknown")
        targets = scope.get("targets", [])
        structured = scope.get("structured_key_diff", [])

        event_id = claim.get("event_id") or f"UT_{int(_created_utc_as_epoch(claim))}"

        summary = {
            "path_changes": len(diff.get("path_changes", [])),
            "schema_changes": len(diff.get("schema_changes", [])),
            "structured_changes": len(diff.get("structured_changes", [])),
        }

        return UpdateEvent(
            event_id=event_id,
            created_utc=str(claim.get("created_utc", "")),
            tool=str(claim.get("tool", "Update Trap (LoKi)")),
            baseline_label=str(diff.get("baseline_label", "baseline")),
            new_label=str(diff.get("new_label", "new")),
            source_profile=source_profile,
            targets=list(targets),
            structured_key_diff=list(structured),
            summary=summary,
            artifacts={
                "claim_pack.json": True,
                "diff_report.json": True,
                "parser_rules.json": True,
                "parser_breakage_assessment.json": payload.get("breakage") is not None,
                "signature_advisory.json": payload.get("advisory") is not None,
            },
        )


def _created_utc_as_epoch(claim: dict) -> float:
    """
    claim_pack.json's created_utc is now an ISO 8601 string (fix applied
    in export.py). This helper supports both that and the older raw
    epoch-float format, so older claim packs still import cleanly.
    """
    raw = claim.get("created_utc", 0)
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(raw)).timestamp()
    except Exception:
        return 0.0
