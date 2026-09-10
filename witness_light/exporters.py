"""
Witness Light — exporters.py
TXT, DOCX, and PDF export.
Fix #5: export_pdf() now uses the _wrap() helper for all text rather than
        silent 120-char truncation via drawString. Long limitation text,
        artifact IDs, and dataset IDs will no longer disappear silently.
"""
from __future__ import annotations

import os
from typing import Iterator

from models import Draft
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from docx import Document


# ── Text ──────────────────────────────────────────────────────────────────────

def export_txt(draft: Draft, out_dir: str, filename: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(draft.as_text() + "\n")
    return path


# ── DOCX ──────────────────────────────────────────────────────────────────────

def export_docx(draft: Draft, out_dir: str, filename: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)

    doc = Document()
    doc.add_heading("Witness Light Draft", level=1)
    doc.add_paragraph(draft.disclaimer)
    doc.add_paragraph("")
    doc.add_paragraph(f"Case ID: {draft.case_id}")
    doc.add_paragraph(f"Purpose: {draft.purpose.value}")
    doc.add_paragraph(f"Intent: {draft.intent.value}")
    doc.add_paragraph(f"Created: {draft.created_time_iso}")
    doc.add_paragraph("")

    for i, p in enumerate(draft.paragraphs, start=1):
        doc.add_paragraph(
            f"{i}. [{p.sentence_class.value}] (Confidence: {p.confidence})"
        )
        doc.add_paragraph(p.text)
        if p.artifact_ids:
            doc.add_paragraph("Sources: " + ", ".join(p.artifact_ids))
        if p.truthloom_dataset_ids:
            doc.add_paragraph("Validation: " + ", ".join(p.truthloom_dataset_ids))
        doc.add_paragraph("")

    if draft.approved:
        doc.add_page_break()
        doc.add_heading("Approval Record", level=2)
        doc.add_paragraph(f"Approved: {draft.approved_time_iso}")
        doc.add_paragraph(f"Approved by: {draft.approved_by}")

    doc.save(path)
    return path


# ── PDF ───────────────────────────────────────────────────────────────────────

def _wrap(text: str, width: int) -> Iterator[str]:
    """Word-wrap text to a maximum character width."""
    words = (text or "").split()
    line: list[str] = []
    n = 0
    for w in words:
        extra = 1 if line else 0
        if n + len(w) + extra > width:
            if line:
                yield " ".join(line)
            line = [w]
            n = len(w)
        else:
            line.append(w)
            n += len(w) + extra
    if line:
        yield " ".join(line)


def export_pdf(draft: Draft, out_dir: str, filename: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)

    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    x = 54
    y = height - 54
    line_h = 14
    wrap_width = 95   # chars per line at Helvetica 10

    def write_line(text: str, bold: bool = False, size: int = 10) -> None:
        """
        FIX #5: Uses _wrap() to handle long lines — no more silent truncation.
        Every character of every line will appear in the PDF.
        """
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        for chunk in _wrap(text, wrap_width):
            if y < 60:
                c.showPage()
                y = height - 54
            c.setFont(font, size)
            c.drawString(x, y, chunk)
            y -= line_h

    def blank() -> None:
        nonlocal y
        y -= line_h * 0.5

    # ── Cover ─────────────────────────────────────────────────────────────────
    write_line("Witness Light — Interpretive Draft", bold=True, size=13)
    blank()

    for line in draft.disclaimer.splitlines():
        write_line(line)
    blank()

    write_line(f"Case ID: {draft.case_id}", bold=True)
    write_line(f"Purpose: {draft.purpose.value}")
    write_line(f"Intent:  {draft.intent.value}")
    write_line(f"Created: {draft.created_time_iso}")
    blank()

    # ── Paragraphs ────────────────────────────────────────────────────────────
    for i, p in enumerate(draft.paragraphs, start=1):
        write_line(
            f"{i}. [{p.sentence_class.value}] (Confidence: {p.confidence})",
            bold=True,
        )
        write_line(p.text)
        if p.artifact_ids:
            write_line("Sources: " + ", ".join(p.artifact_ids))
        if p.truthloom_dataset_ids:
            write_line("Validation: " + ", ".join(p.truthloom_dataset_ids))
        blank()

    # ── Approval record ───────────────────────────────────────────────────────
    if draft.approved:
        c.showPage()
        y = height - 54
        write_line("Approval Record", bold=True, size=12)
        blank()
        write_line(f"Approved:    {draft.approved_time_iso}")
        write_line(f"Approved by: {draft.approved_by}")

    c.save()
    return path
