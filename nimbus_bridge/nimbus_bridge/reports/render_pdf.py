"""
nimbus_bridge/reports/render_pdf.py

PDF rendering stubs — the original pastes all had bare `pass` bodies.
These are kept as explicit stubs rather than removed, so the import
chain is intact and callers can see what functions are expected to
exist here. A real implementation would use a PDF library (reportlab,
weasyprint, etc.) against the JSON outputs from write_meta_reports().
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List


def render_takeout_parse_report(data: Dict[str, Any], out_pdf: Path) -> None:
    raise NotImplementedError("render_takeout_parse_report not yet implemented — see reports/render_pdf.py")


def render_mapping_report(data: Dict[str, Any], out_pdf: Path) -> None:
    raise NotImplementedError("render_mapping_report not yet implemented")


def render_gaps_report(data: Dict[str, Any], out_pdf: Path) -> None:
    raise NotImplementedError("render_gaps_report not yet implemented")


def render_court_packet(pdfs: List[Path], out_pdf: Path) -> None:
    raise NotImplementedError("render_court_packet not yet implemented")
