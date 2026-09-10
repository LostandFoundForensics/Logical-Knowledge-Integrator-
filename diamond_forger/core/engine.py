from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from diamond_forger.core.models import HashJob, JobResult
from diamond_forger.formats.registry import FORMATS, identify


def list_formats() -> List[Dict[str, str]]:
    return [
        {
            "id": f.format_id,
            "label": f.label,
            "description": f.description,
        }
        for f in FORMATS
    ]


def validate_hash_line(hash_line: str) -> HashJob:
    spec = identify(hash_line)
    if not spec:
        return HashJob(format_id="unknown", hash_line=hash_line.strip(), notes="Unrecognized format")
    return HashJob(format_id=spec.format_id, hash_line=hash_line.strip(), notes=spec.label)


def dry_run(hash_line: str) -> JobResult:
    job = validate_hash_line(hash_line)
    if job.format_id == "unknown":
        return JobResult(
            mode="dry_run",
            format_id="unknown",
            accepted=False,
            message="Hash line not recognized. No attempts made.",
            warnings=["Provide a LockBreaker export line or sha256 lab digest."],
        )
    return JobResult(
        mode="dry_run",
        format_id=job.format_id,
        accepted=True,
        message=f"Recognized as {job.format_id}. Dry-run only — no guesses performed.",
        warnings=[
            "Use --execute with examiner + authority to run a bounded dictionary check.",
            "GPU/hashcat farms are out of scope for this module.",
        ],
    )


def dictionary_check(
    hash_line: str,
    wordlist: Path,
    *,
    examiner: str,
    authority: str,
    max_attempts: int = 10_000,
) -> JobResult:
    if len((examiner or "").strip()) < 2:
        return JobResult(
            mode="dictionary",
            format_id="unknown",
            accepted=False,
            message="Examiner identity required (min 2 characters).",
        )
    if len((authority or "").strip()) < 4:
        return JobResult(
            mode="dictionary",
            format_id="unknown",
            accepted=False,
            message="Authority string required (warrant / consent reference).",
        )
    job = validate_hash_line(hash_line)
    if job.format_id == "unknown":
        return JobResult(
            mode="dictionary",
            format_id="unknown",
            accepted=False,
            message="Unrecognized hash line.",
            authority_recorded=True,
        )
    spec = identify(hash_line)
    if not spec or not spec.verify:
        return JobResult(
            mode="dictionary",
            format_id=job.format_id,
            accepted=True,
            message="Format known but no local verifier implemented for full check.",
            authority_recorded=True,
            warnings=["Export to hashcat-compatible tools if authorized."],
        )
    wordlist = Path(wordlist)
    if not wordlist.is_file():
        return JobResult(
            mode="dictionary",
            format_id=job.format_id,
            accepted=False,
            message=f"Wordlist not found: {wordlist}",
            authority_recorded=True,
        )
    attempts = 0
    with wordlist.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if attempts >= max_attempts:
                break
            cand = line.strip()
            if not cand:
                continue
            attempts += 1
            try:
                if spec.verify(cand, job.hash_line):
                    return JobResult(
                        mode="dictionary",
                        format_id=job.format_id,
                        accepted=True,
                        message="Candidate matched under local verifier.",
                        recovered=True,
                        plaintext=cand,
                        attempts=attempts,
                        authority_recorded=True,
                        warnings=[
                            "Handle plaintext as sensitive. Record chain of custody separately.",
                        ],
                    )
            except Exception:
                continue
    return JobResult(
        mode="dictionary",
        format_id=job.format_id,
        accepted=True,
        message="No match within attempt budget.",
        recovered=False,
        attempts=attempts,
        authority_recorded=True,
    )
