from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

from ..domain.models import MetaScope
from ..services.ledger import LedgerActor
from ..services.providers.meta_dyi.parse_runner import run_meta_phase4
from ..reports.meta_reports import write_meta_reports

router = APIRouter()


class MetaPhase4Req(BaseModel):
    case_root: str
    case_id: str
    import_id: str
    vault_root: str
    examiner: str
    machine: str
    user: str
    scope: MetaScope


@router.post("/meta/phase4")
def meta_phase4(req: MetaPhase4Req):
    case_root = Path(req.case_root)
    actor = LedgerActor(examiner=req.examiner, machine=req.machine, user=req.user)
    result = run_meta_phase4(
        case_id=req.case_id,
        case_root=case_root,
        vault_root=Path(req.vault_root),
        import_id=req.import_id,
        actor=actor,
        scope=req.scope,
    )
    reports = write_meta_reports(case_root=case_root, import_id=req.import_id, parse_result=result.model_dump())
    out = result.model_dump()
    out["reports"] = reports
    return out
