from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import JobRequest, JobStatus, LockBreakerResult

DATA_DIR = Path(os.environ.get("LOCKBREAKER_DATA", "./lockbreaker_data")).resolve()

class JobStore:
    def __init__(self):
        for sub in ("statuses", "requests", "results", "artifacts"):
            (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)

    def _p(self, sub: str, job_id: str, ext: str = "json") -> Path:
        return DATA_DIR / sub / f"{job_id}.{ext}"

    def create(self, req: JobRequest) -> JobStatus:
        job_id = f"LB-{uuid.uuid4().hex[:12].upper()}"
        status = JobStatus(
            job_id=job_id,
            status="queued",
            message="Queued for execution",
            updated_at=datetime.now(timezone.utc),
            stage="created",
        )
        self._p("requests", job_id).write_text(req.model_dump_json(indent=2))
        self._p("statuses", job_id).write_text(
            json.dumps(status.model_dump(mode="json"), indent=2)
        )
        return status

    def get_status(self, job_id: str) -> dict:
        p = self._p("statuses", job_id)
        if not p.exists():
            raise FileNotFoundError(f"Job not found: {job_id}")
        return json.loads(p.read_text())

    def get_request(self, job_id: str) -> JobRequest:
        p = self._p("requests", job_id)
        if not p.exists():
            raise FileNotFoundError(f"Job request not found: {job_id}")
        return JobRequest.model_validate_json(p.read_text())

    def set_status(self, job_id: str, status: str, message: str = "", stage: str = "") -> None:
        req = self.get_request(job_id)
        s = JobStatus(
            job_id=job_id,
            status=status,  # type: ignore
            message=message,
            updated_at=datetime.now(timezone.utc),
            stage=stage,
        )
        self._p("statuses", job_id).write_text(
            json.dumps(s.model_dump(mode="json"), indent=2)
        )

    def set_running(self, job_id: str) -> None:
        self.set_status(job_id, "running", "Execution in progress", "running")

    def set_completed(self, job_id: str) -> None:
        self.set_status(job_id, "completed", "Completed successfully", "completed")

    def set_failed(self, job_id: str, reason: str) -> None:
        self.set_status(job_id, "failed", reason, "failed")

    def put_result(self, job_id: str, result: dict) -> None:
        self._p("results", job_id).write_text(json.dumps(result, indent=2))

    def get_result(self, job_id: str) -> dict:
        p = self._p("results", job_id)
        if not p.exists():
            raise FileNotFoundError(f"Result not found: {job_id}")
        return json.loads(p.read_text())

    def get_host_evidence_path(self, job_id: str) -> str:
        req = self.get_request(job_id)
        base = Path(os.environ.get("LOCKBREAKER_EVIDENCE_ROOT", "/var/lockbreaker/evidence"))
        return str(base / req.evidence.case_id / req.evidence.evidence_id)

    def get_host_artifacts_path(self, job_id: str) -> str:
        base = Path(os.environ.get("LOCKBREAKER_ARTIFACTS_ROOT", "/var/lockbreaker/artifacts"))
        return str(base / job_id)
