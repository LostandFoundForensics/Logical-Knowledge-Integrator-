"""
nimbus_bridge/api/routes_nimbus.py

BUG FIXED: the original constructed LedgerActor via
os.getenv("COMPUTERNAME","HOST") / os.getenv("USERNAME","user") —
Windows-only env vars that silently produce wrong values on Linux/macOS.
Fixed: examiner, machine, and user are now explicit request fields.
"""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

from ..paths import CasePaths
from ..services.ledger import NimbusLedger, LedgerActor
from ..services.loki.writer import LokiWriter
from ..services.providers.google_takeout.recognize import recognize_google_takeout
from ..services.providers.google_takeout.parse_runner import run_takeout_parse
from ..domain.models import TakeoutScope

router = APIRouter()


class RecognizeReq(BaseModel):
    case_root: str
    import_id: str
    vault_root: str


@router.post("/takeout/recognize")
def takeout_recognize(req: RecognizeReq):
    return recognize_google_takeout(
        import_id=req.import_id, vault_root=Path(req.vault_root)
    ).model_dump()


class ParseReq(BaseModel):
    case_root: str
    import_id: str
    vault_root: str
    scope: TakeoutScope
    examiner: str
    machine: str
    user: str


@router.post("/takeout/parse")
def takeout_parse(req: ParseReq):
    cp = CasePaths(Path(req.case_root))
    cp.ensure_dirs()

    ledger = NimbusLedger(cp.nimbus_ledger_path())
    actor = LedgerActor(examiner=req.examiner, machine=req.machine, user=req.user)
    loki = LokiWriter(db_path=cp.loki_store, case_id=Path(req.case_root).name)
    loki.init()

    result = run_takeout_parse(
        case_id=Path(req.case_root).name,
        actor=actor,
        ledger=ledger,
        vault_root=Path(req.vault_root),
        takeout_scope=req.scope,
        loki=loki,
        manifest_path=cp.nimbus_manifest_path(req.import_id),
    )
    return result.model_dump()
