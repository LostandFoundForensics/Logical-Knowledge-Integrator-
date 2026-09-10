"""
Sundial — Report PDF
A plain-language, court-ready timeline report. Supports a PLAIN_LARGE reading
mode (bigger type, more spacing) for non-technical reviewers.

Uses reportlab. Wraps text, paginates, and labels inferred events explicitly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _safe(x: Any) -> str:
    return "" if x is None else str(x)


def generate_report_pdf(
    out_pdf: Path,
    case_info,
    records: List[Dict[str, Any]],
    tz_rule: str,
    redaction_summary: Dict[str, Any],
    observed_count: int,
    inferred_count: int,
    reading_mode: str = "STANDARD",
) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    large = (reading_mode == "PLAIN_LARGE")
    body_size = 13 if large else 10
    h1_size = 22 if large else 16
    h2_size = 15 if large else 12
    line_h = (0.26 if large else 0.18) * inch

    c = canvas.Canvas(str(out_pdf), pagesize=LETTER)
    width, height = LETTER
    margin = 0.85 * inch
    x = margin
    y = height - margin

    def page_break(min_space: float = 1.2 * inch) -> None:
        nonlocal y
        if y < min_space:
            c.showPage()
            y = height - margin

    def h1(text: str) -> None:
        nonlocal y
        page_break()
        c.setFont("Helvetica-Bold", h1_size)
        c.drawString(x, y, text)
        y -= line_h * 1.6

    def h2(text: str) -> None:
        nonlocal y
        page_break()
        c.setFont("Helvetica-Bold", h2_size)
        c.drawString(x, y, text)
        y -= line_h * 1.3

    def para(text: str, size: Optional[int] = None) -> None:
        nonlocal y
        size = size or body_size
        c.setFont("Helvetica", size)
        maxw = width - 2 * margin
        for word_line in _wrap(c, text, "Helvetica", size, maxw):
            page_break()
            c.drawString(x, y, word_line)
            y -= line_h

    def kv(k: str, v: str) -> None:
        nonlocal y
        page_break()
        c.setFont("Helvetica-Bold", body_size)
        c.drawString(x, y, f"{k}:")
        c.setFont("Helvetica", body_size)
        c.drawString(x + (2.4 if large else 1.9) * inch, y, v[:120])
        y -= line_h

    # ── Cover ────────────────────────────────────────────────────────────────
    h1("Timeline Report")
    if case_info:
        kv("Case", f"{case_info.case_name} ({case_info.case_id})")
        kv("Owner", _safe(case_info.owner_label))
        kv("Device", _safe(case_info.device_label))
    kv("Observed events", str(observed_count))
    kv("Inferred events", str(inferred_count))
    y -= line_h * 0.5

    h2("How to read this report")
    para(
        "This report lists events in time order. Each event says what was seen "
        "and where it came from. Events marked INFERRED were not directly "
        "recorded; they are reasoned estimates and are labeled as such."
    )
    para(tz_rule)
    if redaction_summary.get("total_redactions", 0) > 0:
        para(
            f"Redaction was applied: {redaction_summary['total_redactions']} item(s) "
            "were masked. The redaction ledger included with this export proves "
            "what was redacted without revealing the original values."
        )

    # ── Timeline ─────────────────────────────────────────────────────────────
    h1("Events")
    if not records:
        para("No events to display for the selected scope.")
    for rec in records:
        page_break(1.4 * inch)
        inferred = rec.get("is_inferred")
        marker = "INFERRED" if inferred else "OBSERVED"
        c.setFont("Helvetica-Bold", body_size)
        c.drawString(x, y, f"[{marker}] {_safe(rec.get('timestamp_start'))}  ({_safe(rec.get('timezone_basis'))})")
        y -= line_h
        para(_safe(rec.get("summary_plain")) or "(no summary)")
        meta_bits = []
        if rec.get("category"):
            meta_bits.append(f"category={rec['category']}")
        if rec.get("confidence") is not None:
            meta_bits.append(f"confidence={rec['confidence']}")
        if rec.get("timestamp_quality"):
            meta_bits.append(f"time={rec['timestamp_quality']}")
        if meta_bits:
            c.setFont("Helvetica-Oblique", body_size - 1)
            page_break()
            c.drawString(x, y, "   " + "  ".join(meta_bits))
            y -= line_h
        if inferred and rec.get("confidence_reasons"):
            for reason in rec["confidence_reasons"][:4]:
                page_break()
                c.setFont("Helvetica", body_size - 1)
                c.drawString(x + 0.2 * inch, y, f"- {reason}")
                y -= line_h
        y -= line_h * 0.4

    # ── Footer on last page ──────────────────────────────────────────────────
    c.setFont("Helvetica", 8)
    c.drawString(x, 0.55 * inch,
                 "Sundial timeline report. Observed events are shown by default; inference is labeled and optional.")
    c.showPage()
    c.save()


def _wrap(c, text: str, font: str, size: int, maxw: float) -> List[str]:
    words = text.split(" ")
    lines: List[str] = []
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font, size) > maxw and line:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines
