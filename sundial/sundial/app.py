"""
Sundial — Web Application
LoKi Timeline Reader. Server-rendered, black & white, usable by a
non-technical reviewer. Every reader action is recorded to the audit log.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sundial.core.audit import AuditLog
from sundial.core.bundle import CaseBundle
from sundial.core.timeline import TimelineEngine, TimelineFilter
from sundial.export.court_export import export_case, ExportOptions

APP_ROOT = Path(__file__).resolve().parent
UI_DIR = APP_ROOT / "ui"

app = FastAPI(title="Sundial", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(UI_DIR / "templates"))

# Single-session reader state. Sundial opens one bundle at a time.
_STATE: dict = {"bundle": None, "audit": None, "bundle_dir": None}


def _audit() -> Optional[AuditLog]:
    return _STATE.get("audit")


@app.on_event("startup")
def _startup():
    # Audit log lives next to wherever a bundle is opened; until then, app-level.
    log = AuditLog(str(APP_ROOT.parent / "sundial_session.log"))
    log.record("APP_OPEN", {"tool": "Sundial"})
    _STATE["audit"] = log


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "bundle_open": _STATE["bundle"] is not None,
        "bundle_dir": _STATE.get("bundle_dir") or "",
    })


@app.post("/open")
def open_bundle(bundle_dir: str = Form(...)):
    # Close any previously open bundle
    if _STATE["bundle"] is not None:
        _STATE["bundle"].close()

    bundle = CaseBundle(bundle_dir)
    status = bundle.open()
    _STATE["bundle"] = bundle
    _STATE["bundle_dir"] = bundle_dir

    # Re-point audit log into the bundle's own logs/ dir when possible
    log_path = Path(bundle_dir) / "logs" / "sundial_session.log"
    _STATE["audit"] = AuditLog(str(log_path))
    _audit().record("CASE_OPEN", {
        "bundle_dir": bundle_dir,
        "db_present": status.db_present,
        "missing": status.missing,
    })

    if not status.case_present:
        return RedirectResponse(url="/?err=nocase", status_code=303)
    return RedirectResponse(url="/case", status_code=303)


@app.get("/case", response_class=HTMLResponse)
def case_view(request: Request):
    bundle: CaseBundle = _STATE["bundle"]
    if bundle is None:
        return RedirectResponse(url="/", status_code=303)

    engine = TimelineEngine(bundle)
    counts = engine.category_counts()
    return templates.TemplateResponse("case.html", {
        "request": request,
        "case": bundle.case_info,
        "status": bundle.status,
        "counts": counts,
    })


@app.get("/timeline", response_class=HTMLResponse)
def timeline_view(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    inferred: int = 0,
    mode: str = "STANDARD",
):
    bundle: CaseBundle = _STATE["bundle"]
    if bundle is None:
        return RedirectResponse(url="/", status_code=303)

    flt = TimelineFilter(
        categories=[category] if category else None,
        search=search or None,
        include_inferred=bool(inferred),
        limit=2000,
    )
    engine = TimelineEngine(bundle)
    result = engine.query(flt)

    _audit().record("BUILD_TIMELINE", {
        "events_loaded": len(result.rows),
        "category": category,
        "observability": "OBSERVED_PLUS_INFERRED" if inferred else "OBSERVED_ONLY",
    })
    if inferred:
        _audit().record("INFERENCE_TOGGLE_SET", {"enabled": True})

    return templates.TemplateResponse("timeline.html", {
        "request": request,
        "case": bundle.case_info,
        "result": result,
        "category": category or "",
        "search": search or "",
        "inferred": int(bool(inferred)),
        "mode": mode,
        "counts": engine.category_counts(),
    })


@app.get("/event/{event_id}", response_class=HTMLResponse)
def event_view(request: Request, event_id: str):
    bundle: CaseBundle = _STATE["bundle"]
    if bundle is None:
        return RedirectResponse(url="/", status_code=303)

    engine = TimelineEngine(bundle)
    detail = engine.event_detail(event_id)
    _audit().record("OPEN_EVENT", {"event_id": event_id, "raw_view_opened": True})

    return templates.TemplateResponse("event.html", {
        "request": request,
        "case": bundle.case_info,
        "detail": detail,
        "event_id": event_id,
    })


@app.get("/export", response_class=HTMLResponse)
def export_form(request: Request):
    bundle: CaseBundle = _STATE["bundle"]
    if bundle is None:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("export.html", {
        "request": request,
        "case": bundle.case_info,
        "done": request.query_params.get("done"),
        "out": request.query_params.get("out", ""),
    })


@app.post("/export/run")
def export_run(
    include_pdf: int = Form(1),
    include_csv: int = Form(1),
    include_jsonl: int = Form(1),
    include_provenance: int = Form(1),
    include_inferred: int = Form(0),
    mask_numbers: int = Form(1),
    hide_contents: int = Form(0),
    reading_mode: str = Form("STANDARD"),
):
    bundle: CaseBundle = _STATE["bundle"]
    if bundle is None:
        return RedirectResponse(url="/", status_code=303)

    options = ExportOptions(
        include_pdf=bool(include_pdf),
        include_csv=bool(include_csv),
        include_jsonl=bool(include_jsonl),
        include_provenance=bool(include_provenance),
        include_inferred=bool(include_inferred),
        mask_numbers=bool(mask_numbers),
        hide_contents=bool(hide_contents),
        reading_mode=reading_mode,
    )

    out_root = str(Path(_STATE["bundle_dir"]) / "exports")
    audit_path = str(_audit().path) if _audit() else None
    result = export_case(bundle, out_root, options, audit_log_path=audit_path)

    _audit().record("EXPORT", {
        "export_dir": result.export_dir,
        "event_count": result.event_count,
        "redaction_total": result.redaction_total,
        "observability": "OBSERVED_PLUS_INFERRED" if options.include_inferred else "OBSERVED_ONLY",
    })

    return RedirectResponse(url=f"/export?done=1&out={result.export_dir}", status_code=303)
