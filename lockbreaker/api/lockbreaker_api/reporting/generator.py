from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .text_renderer import render_text
from .pdf_renderer import render_pdf
from .models import CourtReportInput


def generate_court_report(
    result_json: Dict[str, Any],
    output_dir: Path,
    examiner_name: str,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def _parse_dt(s: str) -> datetime:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()

    r = CourtReportInput(
        job_id=result_json["job_id"],
        case_id=result_json["case_id"],
        evidence_id=result_json["evidence_id"],
        evidence_filename=result_json.get("artifacts", {}).get("source_filename", "unknown"),
        evidence_sha256=result_json.get("provenance", {}).get("evidence_sha256", "unknown"),
        profile_name=result_json.get("profile_id", "unknown"),
        profile_description="See LockBreaker profile library for full methodology description.",
        authorization_basis=result_json.get("audit", {}).get("authorization_basis", "unknown"),
        authorization_reference=result_json.get("audit", {}).get("authorization_ref", "unknown"),
        examiner=examiner_name,
        organization="Lost & Found Forensics",
        started_at=_parse_dt(result_json.get("started_at", datetime.utcnow().isoformat())),
        finished_at=_parse_dt(result_json.get("finished_at", datetime.utcnow().isoformat())),
        findings=result_json.get("findings", []),
        artifacts=result_json.get("artifacts", {}),
        signature_sha256=result_json.get("audit", {}).get("signature", "unsigned"),
        signed_at=result_json.get("audit", {}).get("signed_at", "unknown"),
    )

    text = render_text(r)
    pdf_bytes = render_pdf(text)

    (output_dir / "LockBreaker_Report.pdf").write_bytes(pdf_bytes)
    (output_dir / "LockBreaker_Result.json").write_text(
        json.dumps(result_json, indent=2), encoding="utf-8"
    )

    replay = f"""
LOCKBREAKER REPLAY INSTRUCTIONS (QUALIFIED EXAMINER USE)

This packet allows an independent qualified examiner to verify these results.

1. VERIFY INTEGRITY
   - Check LockBreaker_Result.json audit.signature using the public verify key.
   - Endpoint: GET /api/v1/verify-key
   - Tool: POST /api/v1/results/verify with the result JSON.

2. VERIFY EVIDENCE
   - Confirm SHA256 of original evidence matches provenance.evidence_sha256.

3. REPRODUCE
   - Use same LockBreaker version (see worker_version in result).
   - Use same profile_id.
   - Use same wordlist and ruleset SHA256s from the plan.
   - Run against same evidence (or hash-verified copy).

4. COMPARE
   - Results must match. Any deviation must be documented and investigated.

5. DOCTRINE VERIFICATION
   - Verify doctrine_digest_sha256 matches the doctrine pack used.
   - Request doctrine pack from examining agency if needed.

NOTE: This replay is intended for qualified digital forensic practitioners only.
Results produced under court order or warrant. Handle under appropriate legal authority.
""".strip()

    (output_dir / "LockBreaker_Replay.txt").write_text(replay, encoding="utf-8")
