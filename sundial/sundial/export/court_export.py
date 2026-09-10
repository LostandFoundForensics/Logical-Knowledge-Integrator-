"""
Sundial — Court Export
Produces a self-contained, hash-verified export bundle:

Sundial_Export_<case>_<timestamp>/
  README.txt
  Report.pdf
  timeline.csv
  timeline.jsonl
  provenance.csv
  redaction_ledger.json
  hash_manifest.txt
  export_session_auditlog.jsonl
  case.json (copy)
  export_metadata.json

Every output file is hashed into hash_manifest.txt. Redaction is proven via
the SHA-256 ledger. No new analysis happens at export — it compiles what the
timeline already holds.
"""
from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sundial.core.audit import sha256_file, utc_now_iso
from sundial.core.bundle import CaseBundle
from sundial.core.redaction import (
    number_rules, redact_obj, summarize_redactions,
)
from sundial.core.timeline import TimelineEngine, TimelineFilter


TOOL_VERSION = "Sundial/0.5.0"


@dataclass
class ExportOptions:
    include_pdf: bool = True
    include_csv: bool = True
    include_jsonl: bool = True
    include_provenance: bool = True
    include_inferred: bool = False        # observed-only by default
    mask_numbers: bool = True
    hide_contents: bool = False
    reading_mode: str = "STANDARD"        # STANDARD | PLAIN_LARGE


@dataclass
class ExportResult:
    export_dir: str
    files: List[str] = field(default_factory=list)
    event_count: int = 0
    redaction_total: int = 0
    notes: List[str] = field(default_factory=list)


def export_case(
    bundle: CaseBundle,
    out_root: str,
    options: ExportOptions,
    audit_log_path: Optional[str] = None,
) -> ExportResult:
    case = bundle.case_info
    case_id = case.case_id if case else "UNKNOWN"
    case_name = case.case_name if case else "Untitled"

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Keep the folder name short and filesystem-safe: a full UUID case_id plus
    # timestamp can exceed path limits on some systems. Use a short slug.
    safe_case = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in case_id)[:16]
    export_dir = Path(out_root) / f"Sundial_Export_{safe_case}_{ts}"
    export_dir.mkdir(parents=True, exist_ok=True)

    engine = TimelineEngine(bundle)
    result = engine.query(TimelineFilter(
        include_inferred=options.include_inferred, limit=1_000_000
    ))

    rules = number_rules() if options.mask_numbers else []

    # ── Build the per-event records (redacted) ───────────────────────────────
    records: List[Dict[str, Any]] = []
    all_redaction_events: List[Dict[str, Any]] = []
    for row in result.rows:
        rec = {
            "event_id": row.event_id,
            "category": row.category,
            "timestamp_start": row.timestamp_start,
            "timestamp_end": row.timestamp_end,
            "timestamp_quality": row.timestamp_quality,
            "timezone_basis": row.timezone_basis,
            "observability": row.observability,
            "confidence": row.confidence,
            "summary_plain": row.summary_plain,
            "summary_technical": row.summary_technical,
            "is_inferred": row.is_inferred,
            "confidence_level": row.confidence_level,
            "confidence_reasons": row.confidence_reasons,
        }
        if rules or options.hide_contents:
            rec, ev = redact_obj(rec, rules, hide_contents=options.hide_contents)
            all_redaction_events.extend(ev)
        records.append(rec)

    written: List[Path] = []

    # ── timeline.jsonl ───────────────────────────────────────────────────────
    if options.include_jsonl:
        p = export_dir / "timeline.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        written.append(p)

    # ── timeline.csv ─────────────────────────────────────────────────────────
    if options.include_csv:
        p = export_dir / "timeline.csv"
        cols = ["event_id", "category", "timestamp_start", "timestamp_end",
                "timestamp_quality", "timezone_basis", "observability",
                "confidence", "is_inferred", "summary_plain"]
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for rec in records:
                w.writerow(rec)
        written.append(p)

    # ── provenance.csv ───────────────────────────────────────────────────────
    if options.include_provenance and bundle.has_table("event_sources"):
        p = export_dir / "provenance.csv"
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["event_id", "source_path", "source_type", "table_name",
                        "record_id", "parser_name", "parser_version"])
            for rec in records:
                for src in engine._sources_for(rec["event_id"]):
                    w.writerow([
                        rec["event_id"], src.get("source_path"), src.get("source_type"),
                        src.get("table_name"), src.get("record_id"),
                        src.get("parser_name"), src.get("parser_version"),
                    ])
        written.append(p)

    # ── redaction_ledger.json ────────────────────────────────────────────────
    redaction_summary = summarize_redactions(all_redaction_events)
    p = export_dir / "redaction_ledger.json"
    p.write_text(json.dumps({
        "enabled": bool(rules) or options.hide_contents,
        "mask_numbers": options.mask_numbers,
        "hide_contents": options.hide_contents,
        "summary": redaction_summary,
        "events": all_redaction_events[:5000],
        "created_utc": utc_now_iso(),
    }, indent=2), encoding="utf-8")
    written.append(p)

    # ── Report.pdf ───────────────────────────────────────────────────────────
    if options.include_pdf:
        from sundial.export.report_pdf import generate_report_pdf
        p = export_dir / "Report.pdf"
        generate_report_pdf(
            p,
            case_info=case,
            records=records,
            tz_rule=result.display_timezone_rule,
            redaction_summary=redaction_summary,
            observed_count=result.observed_count,
            inferred_count=result.inferred_count,
            reading_mode=options.reading_mode,
        )
        written.append(p)

    # ── case.json copy ───────────────────────────────────────────────────────
    src_case = bundle.bundle_dir / "case.json"
    if src_case.exists():
        dst = export_dir / "case.json"
        shutil.copy2(src_case, dst)
        written.append(dst)

    # ── export_session_auditlog.jsonl copy ───────────────────────────────────
    if audit_log_path and Path(audit_log_path).exists():
        dst = export_dir / "export_session_auditlog.jsonl"
        shutil.copy2(audit_log_path, dst)
        written.append(dst)

    # ── export_metadata.json ─────────────────────────────────────────────────
    meta = {
        "tool": "Sundial",
        "tool_version": TOOL_VERSION,
        "generated_utc": utc_now_iso(),
        "case_id": case_id,
        "case_name": case_name,
        "included": {
            "pdf": options.include_pdf,
            "csv": options.include_csv,
            "jsonl": options.include_jsonl,
            "provenance": options.include_provenance,
        },
        "redactions": {
            "mask_numbers": options.mask_numbers,
            "hide_contents": options.hide_contents,
        },
        "observability": "OBSERVED_PLUS_INFERRED" if options.include_inferred else "OBSERVED_ONLY",
        "counts": {
            "observed": result.observed_count,
            "inferred": result.inferred_count,
        },
    }
    p = export_dir / "export_metadata.json"
    p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    written.append(p)

    # ── README.txt ───────────────────────────────────────────────────────────
    readme = export_dir / "README.txt"
    readme.write_text(_readme_text(case_name, case_id, options, result), encoding="utf-8")
    written.append(readme)

    # ── hash_manifest.txt (hash every file last) ─────────────────────────────
    manifest = export_dir / "hash_manifest.txt"
    lines = []
    for fp in written:
        lines.append(f"SHA256  {sha256_file(str(fp))}  {fp.name}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written.append(manifest)

    return ExportResult(
        export_dir=str(export_dir),
        files=[f.name for f in written],
        event_count=len(records),
        redaction_total=redaction_summary["total_redactions"],
        notes=result.notes,
    )


def _readme_text(case_name: str, case_id: str, opt: ExportOptions, result) -> str:
    obs = "Observed events only." if not opt.include_inferred else \
        "Observed events plus inferred events (inference is clearly labeled)."
    return (
        "SUNDIAL EXPORT\n"
        "==============\n\n"
        f"Case: {case_name} ({case_id})\n"
        f"Generated: {utc_now_iso()}\n"
        f"Tool: {TOOL_VERSION}\n\n"
        "WHAT THIS IS\n"
        f"{obs}\n"
        f"Observed events: {result.observed_count}\n"
        f"Inferred events: {result.inferred_count}\n\n"
        "TIMEZONE\n"
        f"{result.display_timezone_rule}\n\n"
        "REDACTION\n"
        f"Phone/email masking: {'ON' if opt.mask_numbers else 'OFF'}\n"
        f"Message contents hidden: {'YES' if opt.hide_contents else 'NO'}\n"
        "See redaction_ledger.json. The ledger proves what was redacted using\n"
        "SHA-256 hashes; it does not contain the original values.\n\n"
        "VERIFYING THIS EXPORT\n"
        "Each file in this folder is listed in hash_manifest.txt with its\n"
        "SHA-256. Recompute the hashes to confirm nothing changed after export.\n\n"
        "FILES\n"
        "Report.pdf .............. human-readable timeline report\n"
        "timeline.csv ............ one row per event (spreadsheet-friendly)\n"
        "timeline.jsonl .......... one JSON object per event (machine-friendly)\n"
        "provenance.csv .......... source artifact for each event\n"
        "redaction_ledger.json ... proof of redaction\n"
        "export_metadata.json .... what was included and how\n"
        "hash_manifest.txt ....... SHA-256 of every file here\n"
    )
