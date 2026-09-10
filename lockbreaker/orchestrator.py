"""
LockBreaker orchestrator — the spine of every job.

  1. Survey access surfaces (always)
  2. Gate authorization (for anything beyond survey)
  3. Extract material from authorized surfaces (RO)
  4. Recovery phase (dry-run default)
  5. Write audit + result bundle
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from lockbreaker.auth.gate import Authorization, require_authorization
from lockbreaker.doctrine.profiles import get_profile, Profile
from lockbreaker.ledger.audit import AuditLedger
from lockbreaker.surfaces.survey import survey_access_surfaces, summarize_survey
from lockbreaker.extract.android_lock import (
    extract_locksettings,
    extract_gesture_key,
    extract_android_lock_bundle,
)
from lockbreaker.extract.ios_backup_hash import extract_ios_backup_hash
from lockbreaker.attack.dry_run import run_dry_run
from lockbreaker.attack.hashcat_bridge import run_hashcat_phase, real_backends_enabled


def run_job(
    *,
    profile_id: str,
    case_dir: str,
    auth: Optional[Authorization] = None,
    evidence_root: Optional[str] = None,
    backup_path: Optional[str] = None,
    hash_file: Optional[str] = None,
    wordlist: Optional[str] = None,
    examiner: str = "",
) -> Dict[str, Any]:
    profile = get_profile(profile_id)
    case = Path(case_dir)
    case.mkdir(parents=True, exist_ok=True)
    ledger = AuditLedger(case / "lockbreaker_audit.jsonl")
    work = case / "work"
    work.mkdir(exist_ok=True)

    started = int(time.time())
    ledger.record(
        "JOB_STARTED",
        examiner=examiner or (auth.examiner if auth else ""),
        details={"profile_id": profile_id, "case_dir": str(case)},
    )

    # ── Phase 0: Survey ─────────────────────────────────────────────
    ctx = {
        "evidence_root": evidence_root,
        "android_dump": evidence_root,
        "backup_path": backup_path,
        "hash_file": hash_file,
        "case_path": str(case),
    }
    surfaces = survey_access_surfaces(ctx)
    survey_summary = summarize_survey(surfaces)
    ledger.record("SURVEY_COMPLETE", examiner=examiner, details=survey_summary)
    (case / "survey.json").write_text(
        json.dumps(survey_summary, indent=2), encoding="utf-8"
    )

    if profile_id == "survey_only":
        result = {
            "ok": True,
            "profile_id": profile_id,
            "phase": "survey_only",
            "survey": survey_summary,
            "message": "Survey complete. No recovery attempted.",
            "found": False,
            "started_epoch": started,
            "finished_epoch": int(time.time()),
        }
        _write_result(case, result)
        ledger.record("JOB_FINISHED", examiner=examiner, details={"found": False})
        return result

    # ── Auth gate ───────────────────────────────────────────────────
    if auth is None:
        raise PermissionError(
            "Authorization is required for profile "
            f"'{profile_id}'. Pass basis, reference_id, and examiner."
        )
    require_authorization(auth, profile)
    ledger.record(
        "AUTH_ACCEPTED",
        examiner=auth.examiner,
        details={"basis": auth.basis, "reference_id": auth.reference_id, "profile_id": profile_id},
    )

    # ── Required surfaces check ─────────────────────────────────────
    available = set(survey_summary["available"])
    missing = [s for s in profile.required_surfaces if s not in available]
    if missing and profile.required_surfaces:
        # ANDROID-FOLDER-DUMP may still allow locksettings detection partial
        msg = f"Required access surfaces not available: {', '.join(missing)}"
        ledger.record("SURFACE_MISSING", examiner=auth.examiner, details={"missing": missing})
        result = {
            "ok": False,
            "profile_id": profile_id,
            "phase": "surface_check",
            "survey": survey_summary,
            "message": msg,
            "found": False,
            "started_epoch": started,
            "finished_epoch": int(time.time()),
        }
        _write_result(case, result)
        return result

    # ── Phase 1: Extract ────────────────────────────────────────────
    artifacts: List[Dict[str, Any]] = []
    extract_notes: List[str] = []
    extract_meta: Dict[str, Any] = {}

    android_extractors = {"android_locksettings", "android_pattern"}
    if evidence_root and android_extractors.intersection(profile.extractors):
        r = extract_android_lock_bundle(Path(evidence_root), work)
        extract_notes.append(r.get("message") or "")
        artifacts.extend(r.get("artifacts") or [])
        extract_meta["android"] = {
            "era": r.get("era"),
            "outlook": r.get("offline_recovery_outlook"),
            "kinds": r.get("credential_kinds_seen"),
            "warnings": r.get("warnings"),
        }

    if backup_path and "ios_backup_manifest" in profile.extractors:
        r = extract_ios_backup_hash(Path(backup_path), work)
        extract_notes.append(r.get("message") or "")
        artifacts.extend(r.get("artifacts") or [])
        extract_meta["ios_backup"] = {
            "encrypted": r.get("encrypted"),
            "generation": r.get("generation"),
            "suggested_hashcat_mode": r.get("suggested_hashcat_mode"),
        }

    if hash_file and Path(hash_file).is_file():
        artifacts.append({"path": str(Path(hash_file).resolve()), "kind": "hash_file"})

    ledger.record(
        "EXTRACT_COMPLETE",
        examiner=auth.examiner,
        details={"artifacts": artifacts, "notes": extract_notes},
    )

    # ── Phase 2: Recovery ───────────────────────────────────────────
    strategy = next(
        (s for s in profile.attack_strategies if s != "dry_run_only"),
        "dry_run_only",
    )
    if strategy == "dry_run_only" or not real_backends_enabled():
        attack_result = run_dry_run(
            profile_id=profile_id,
            strategy=strategy,
            artifacts=artifacts,
        )
    else:
        attack_result = run_hashcat_phase(
            profile_id=profile_id,
            strategy=strategy,
            artifacts=artifacts,
            work_dir=work / "hashcat",
            wordlist=Path(wordlist) if wordlist else None,
        )

    ledger.record(
        "ATTACK_COMPLETE",
        examiner=auth.examiner,
        details={
            "backend": attack_result.get("backend"),
            "found": attack_result.get("found"),
            "message": attack_result.get("message"),
        },
    )

    finished = int(time.time())
    result = {
        "ok": bool(attack_result.get("ok", True)),
        "profile_id": profile_id,
        "phase": "complete",
        "survey": survey_summary,
        "extract_notes": extract_notes,
        "extract_meta": extract_meta,
        "artifacts": artifacts,
        "attack": attack_result,
        "found": bool(attack_result.get("found")),
        "authorization": {
            "basis": auth.basis,
            "reference_id": auth.reference_id,
            "examiner": auth.examiner,
        },
        "real_backends_enabled": real_backends_enabled(),
        "started_epoch": started,
        "finished_epoch": finished,
        "duration_seconds": finished - started,
        "message": attack_result.get("message", ""),
    }
    _write_result(case, result)
    ledger.record(
        "JOB_FINISHED",
        examiner=auth.examiner,
        details={"found": result["found"], "duration_seconds": result["duration_seconds"]},
    )
    return result


def _write_result(case: Path, result: Dict[str, Any]) -> None:
    (case / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
