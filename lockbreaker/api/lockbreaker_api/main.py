from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio

from .models import JobRequest
from .storage import JobStore
from .authz import validate_authorization
from .signer import sign_result, verify_result, get_verify_key_b64
from .eca import suggest_context, apply_examiner_decisions
from .ake import compose_strategy, generate_owner_wordlist
from .orchestration.pipeline import orchestrate_run, build_review_summary
from .profiles.loader import load_profile, load_all_profiles
from .profiles.translator import translate_to_execution_plan
from .reporting.generator import generate_court_report

app = FastAPI(
    title="LockBreaker API",
    version="1.0.0",
    description=(
        "LockBreaker: Court-grade mobile credential recovery system. "
        "Authorized use only. All actions are logged and signed."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production to LoKi UI origin
    allow_methods=["*"],
    allow_headers=["*"],
)

store = JobStore()
RUNNER_BASE = "http://lockbreaker-runner:9000"

# ── Rate limiting ─────────────────────────────────────────────────────────────
from collections import defaultdict
import time as _time
_rate_log: dict = defaultdict(list)

def _check_rate(examiner: str, max_per_hour: int = 20) -> None:
    now = _time.time()
    _rate_log[examiner] = [t for t in _rate_log[examiner] if now - t < 3600]
    if len(_rate_log[examiner]) >= max_per_hour:
        raise HTTPException(429, f"Job rate limit exceeded ({max_per_hour}/hour). Contact administrator.")
    _rate_log[examiner].append(now)


# ── Profiles ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/profiles")
def list_profiles():
    profiles = load_all_profiles()
    return {"profiles": [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "category": p.get("category"),
            "description": p.get("description"),
            "legal": p.get("legal", {}),
        }
        for p in profiles
    ]}

@app.get("/api/v1/profiles/{profile_id}")
def get_profile(profile_id: str):
    try:
        return load_profile(profile_id)
    except KeyError:
        raise HTTPException(404, f"Profile not found: {profile_id}")


# ── Evidence Context Analysis ─────────────────────────────────────────────────

@app.post("/api/v1/eca/suggest")
def eca_suggest(evidence: Dict[str, Any]):
    """Returns context suggestions from evidence metadata. No action is taken."""
    suggestions = suggest_context(evidence)
    return {"suggestions": suggestions}

@app.post("/api/v1/eca/confirm")
def eca_confirm(body: Dict[str, Any]):
    """Applies examiner decisions to suggestions, returns confirmed_context for AKE."""
    suggestions = body.get("suggestions", [])
    decisions = body.get("decisions", [])
    confirmed = apply_examiner_decisions(suggestions, decisions)
    return {"confirmed_context": confirmed}


# ── Job lifecycle ─────────────────────────────────────────────────────────────

@app.post("/api/v1/jobs")
def create_job(req: JobRequest):
    _check_rate(req.submitted_by)
    validate_authorization(req)
    status = store.create(req)
    return status.model_dump(mode="json")

@app.get("/api/v1/jobs/{job_id}/status")
def job_status(job_id: str):
    try:
        return store.get_status(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")

@app.get("/api/v1/jobs/{job_id}/stream")
async def stream_status(job_id: str):
    """Server-Sent Events stream for live job progress."""
    async def _generate():
        while True:
            try:
                status = store.get_status(job_id)
                yield f"data: {json.dumps(status)}\n\n"
                if status.get("status") in ("completed", "failed", "rejected"):
                    break
            except FileNotFoundError:
                yield f"data: {json.dumps({'error': 'job_not_found'})}\n\n"
                break
            await asyncio.sleep(5)
    return StreamingResponse(_generate(), media_type="text/event-stream")

@app.post("/api/v1/jobs/{job_id}/review")
def review_job(job_id: str):
    """Returns a court-safe summary of what will happen before execution."""
    try:
        req_model = store.get_request(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")

    profile = load_profile(req_model.attack_profile)
    tr = translate_to_execution_plan(req_model, profile)
    if not tr.ok:
        raise HTTPException(400, {"errors": tr.errors})

    # Stub doctrine for review (full doctrine wired in run)
    doctrine_stub = {
        "format_id": "(will be determined at runtime)",
        "recipe_id": "(determined by doctrine engine)",
        "primary_backend": (profile.get("execution_plan", {}) or {})
                           .get("backend_priority", ["john"])[0],
        "fallback_backend": "hashcat",
        "doctrine_digest_sha256": "(computed at run time)",
        "rationale": profile.get("description", ""),
    }
    return build_review_summary(profile, tr.plan.__dict__, doctrine_stub)

@app.post("/api/v1/jobs/{job_id}/run")
def run_job(job_id: str, background_tasks: BackgroundTasks):
    """Dispatches job to background execution. Returns immediately."""
    try:
        req_model = store.get_request(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")

    current = store.get_status(job_id)
    if current.get("status") == "running":
        raise HTTPException(409, "Job is already running")

    store.set_running(job_id)
    background_tasks.add_task(_execute_job, job_id)
    return {"ok": True, "job_id": job_id, "status": "running"}

@app.post("/api/v1/jobs/{job_id}/run-dry")
def run_dry(job_id: str):
    """Dry-run: validates, signs, and completes job without real execution."""
    try:
        req_model = store.get_request(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "job_id": job_id,
        "case_id": req_model.evidence.case_id,
        "evidence_id": req_model.evidence.evidence_id,
        "profile_id": req_model.attack_profile,
        "worker_version": "lockbreaker-dryrun-1.0",
        "started_at": now,
        "finished_at": now,
        "findings": [],
        "artifacts": {},
        "provenance": {"evidence_sha256": req_model.evidence.sha256},
        "audit": {
            "authorization_basis": req_model.authorization.basis,
            "authorization_ref": req_model.authorization.reference_id,
            "dry_run": True,
        },
    }
    signed = sign_result(result)
    store.put_result(job_id, signed)
    store.set_completed(job_id)
    return {"ok": True, "job_id": job_id, "note": "dry-run completed"}

@app.get("/api/v1/jobs/{job_id}/result")
def get_result(job_id: str):
    try:
        return store.get_result(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Result not yet available")

@app.post("/api/v1/results/verify")
def verify(body: Dict[str, Any]):
    """Verifies a signed LockBreaker result. Available to any party."""
    ok, message = verify_result(body)
    return {"verified": ok, "message": message}

@app.get("/api/v1/verify-key")
def get_verify_key():
    """Returns the public ed25519 verify key. Safe to share."""
    return {"verify_key": get_verify_key_b64(), "algorithm": "ed25519"}


# ── Background execution ──────────────────────────────────────────────────────

def _execute_job(job_id: str) -> None:
    """Background task: full orchestration pipeline."""
    try:
        req_model = store.get_request(job_id)
        req = req_model.model_dump(mode="json")
        profile = load_profile(req_model.attack_profile)

        # Generate owner-derived wordlist if context available
        examiner_inputs = req.get("examiner_inputs") or {}
        confirmed_context = {
            "owner_name": examiner_inputs.get("owner_name"),
            "year_hint": None,
        }

        artifacts_path = Path(store.get_host_artifacts_path(job_id))
        generate_owner_wordlist(confirmed_context, artifacts_path / "owner_derived.txt")

        tr = translate_to_execution_plan(req_model, profile)
        if not tr.ok:
            store.set_failed(job_id, f"Plan generation failed: {tr.errors}")
            return

        out = orchestrate_run(
            runner_base=RUNNER_BASE,
            job_id=job_id,
            job_request=req,
            profile=profile,
            plan=tr.plan.__dict__,
            host_evidence_path=store.get_host_evidence_path(job_id),
            host_artifacts_path=store.get_host_artifacts_path(job_id),
        )

        if not out.get("ok"):
            store.set_failed(job_id, out.get("stage", "unknown_failure"))
            return

        store.set_completed(job_id)

    except Exception as e:
        store.set_failed(job_id, str(e))
