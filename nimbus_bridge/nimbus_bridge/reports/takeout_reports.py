"""
nimbus_bridge/reports/takeout_reports.py

Referenced in the package tree but never provided as code — stub
matching the same pattern as render_pdf.py.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


def write_takeout_reports(*, case_root: Path, import_id: str, parse_result: Dict[str, Any]) -> Dict[str, str]:
    out_dir = case_root / "exports" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"takeout_parse_{import_id}.json"
    out_path.write_text(json.dumps(parse_result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return {"takeout_parse_json": str(out_path)}
