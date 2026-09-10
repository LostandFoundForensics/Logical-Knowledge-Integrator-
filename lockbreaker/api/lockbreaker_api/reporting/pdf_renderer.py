from __future__ import annotations
from io import BytesIO

try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    _REPORTLAB = True
except ImportError:
    _REPORTLAB = False


def render_pdf(text: str) -> bytes:
    if not _REPORTLAB:
        # Fallback: return text as bytes with PDF-like wrapper note
        return (
            b"%PDF-1.4 (reportlab not installed - text content follows)\n"
            + text.encode("utf-8")
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="LockBreaker Forensic Report",
        author="LockBreaker — Lost & Found Forensics",
    )

    styles = getSampleStyleSheet()
    mono = ParagraphStyle(
        "mono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=13,
        spaceAfter=4,
    )
    heading = ParagraphStyle(
        "heading",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    story = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            story.append(Spacer(1, 6))
            continue
        if block.startswith("━") or block.isupper() and len(block) < 60:
            style = heading
        else:
            style = mono
        safe = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe.replace("\n", "<br/>"), style))
        story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()
