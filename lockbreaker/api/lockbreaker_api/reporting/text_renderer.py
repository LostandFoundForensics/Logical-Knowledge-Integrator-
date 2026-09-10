from __future__ import annotations
from .models import CourtReportInput


def render_text(r: CourtReportInput) -> str:
    duration = r.finished_at - r.started_at

    if r.findings:
        findings_text = "\n".join(
            f"  - Item: {f.get('item', 'N/A')}\n"
            f"    Recovered Value: {f.get('value', '[REDACTED]')}\n"
            f"    Method: {f.get('method', 'N/A')}\n"
            f"    Complexity: {f.get('complexity', 'N/A')}\n"
            f"    Note: {f.get('court_note', '')}"
            for f in r.findings
        )
    else:
        findings_text = (
            "  No recoverable credentials were identified during the "
            "authorized examination period under the approved conditions and time limits."
        )

    return f"""
LOCKBREAKER DIGITAL FORENSICS REPORT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CASE IDENTIFICATION
   Case ID:      {r.case_id}
   Evidence ID:  {r.evidence_id}
   Job ID:       {r.job_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LEGAL AUTHORITY & SCOPE
   This examination was conducted under the following legal authority:
   Basis:     {r.authorization_basis}
   Reference: {r.authorization_reference}

   The scope was strictly limited to authorized credential recovery
   from lawfully obtained digital evidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. EVIDENCE
   Filename:  {r.evidence_filename}
   SHA256:    {r.evidence_sha256}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. PURPOSE
   To determine whether authorized access credentials could be
   recovered from the submitted evidence in support of the investigation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. METHODOLOGY (PLAIN LANGUAGE)
   LockBreaker was used to analyze the evidence using a predefined,
   court-reviewed recovery profile:

   Profile:     {r.profile_name}
   Description: {r.profile_description}

   Process:
   - Evidence was accessed in read-only mode
   - A structured, time-bounded recovery strategy was applied
   - All actions were logged and cryptographically signed
   - No destructive actions were performed on any evidence

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. RESULTS
{findings_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. INTEGRITY & VERIFICATION
   All results were cryptographically signed using ed25519.
   Any party can independently verify these results using the
   public verify key and the accompanying LockBreaker_Result.json.
   See LockBreaker_Replay.txt for verification instructions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

8. LIMITATIONS
   - Analysis is limited to the evidence provided and authorized scope
   - Absence of recovered credentials does not confirm non-existence
   - Time limits, encryption strength, and evidence completeness
     affect recovery probability
   - Results represent pattern observations only

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

9. EXAMINER ATTESTATION
   I attest this examination was conducted in accordance with accepted
   digital forensic practices, within authorized scope, using
   LockBreaker — a purpose-built mobile forensics credential recovery system.

   Examiner:     {r.examiner}
   Organization: {r.organization}
   Duration:     {duration}
   Started:      {r.started_at.isoformat()}
   Finished:     {r.finished_at.isoformat()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

10. CRYPTOGRAPHIC VERIFICATION
    Signature (ed25519): {r.signature_sha256}
    Signed At:           {r.signed_at}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF LOCKBREAKER FORENSIC REPORT
""".strip()
