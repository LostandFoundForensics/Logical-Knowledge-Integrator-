"""
Update Trap — core/dashboard.py
Builds the "LOKI UPDATE READINESS STATUS" board: a TXT/CSV/JSON summary
of which parsers are at risk after an observed update, what advisory
signatures matched, and what human actions remain outstanding.
"""
from __future__ import annotations
import json
import os
import csv
from typing import Any, Dict


def build_dashboard(bundle_dir: str, payload: Dict[str, Any]) -> None:
    diff = payload.get("diff_report", {})
    breakage = payload.get("breakage") or []
    advisory = payload.get("advisory") or []
    claim = payload.get("claim_pack", {})

    scope = claim.get("scope") or {}
    profile = scope.get("source_profile", "unknown")
    targets = scope.get("targets", [])
    structured = scope.get("structured_key_diff", [])

    event_id = claim.get("event_id", "unknown_event")

    high, med, low = [], [], []
    for f in breakage:
        lvl = f.get("risk_level", "medium").lower()
        if lvl == "high":
            high.append(f)
        elif lvl == "low":
            low.append(f)
        else:
            med.append(f)

    # ── TXT ───────────────────────────────────────────────────────────────────
    txt_path = os.path.join(bundle_dir, "dashboard.txt")
    with open(txt_path, "w", encoding="utf-8") as w:
        w.write("UPDATE TRAP — ZERO-DAY DASHBOARD\n")
        w.write(f"Event: {event_id}\n")
        w.write(f"Baseline: {diff.get('baseline_label', 'baseline')}    New: {diff.get('new_label', 'new')}\n")
        w.write(f"Source Profile: {profile}\n")
        w.write(f"Targets: {', '.join(targets) if targets else '(none)'}\n")
        w.write(f"Structured-key diff: {', '.join(structured) if structured else '(none)'}\n\n")

        w.write("OBSERVED CHANGES\n")
        w.write(f"- Path changes: {len(diff.get('path_changes', []))}\n")
        w.write(f"- SQLite schema changes: {len(diff.get('schema_changes', []))}\n")
        w.write(f"- Structured-key changes: {len(diff.get('structured_changes', []))}\n\n")

        w.write("TOP RISKS (PARSERS)\n")
        if high:
            w.write("HIGH:\n")
            for f in high[:10]:
                w.write(f"  - {f.get('parser_id')}\n")
                for r in f.get("reasons", [])[:5]:
                    w.write(f"      * {r}\n")
        if med:
            w.write("MEDIUM:\n")
            for f in med[:10]:
                w.write(f"  - {f.get('parser_id')}\n")
                for r in f.get("reasons", [])[:5]:
                    w.write(f"      * {r}\n")
        if not (high or med):
            w.write("(none)\n")

        w.write("\nADVISORY SIGNATURES (NON-DETERMINISTIC)\n")
        if advisory:
            for a in advisory[:10]:
                w.write(f"- {a.get('id', '(unknown)')} (matched_patterns={a.get('matched_patterns', 0)})\n")
        else:
            w.write("(none)\n")

        w.write("\nACTIONS REQUIRED (HUMAN)\n")
        w.write("[ ] Review Suggested Patches\n")
        w.write("[ ] Approve Column Maps\n")
        w.write("[ ] Re-run validation against known-good dataset (Truthloom)\n")

    # ── CSV risk list ─────────────────────────────────────────────────────────
    csv_path = os.path.join(bundle_dir, "dashboard_parsers.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        cw.writerow(["parser_id", "risk_level", "reason_count", "reasons_sample"])
        for entry in breakage:
            reasons = entry.get("reasons", [])
            cw.writerow([
                entry.get("parser_id", ""),
                entry.get("risk_level", ""),
                len(reasons),
                " | ".join(reasons[:3]),
            ])

    # ── JSON ──────────────────────────────────────────────────────────────────
    json_path = os.path.join(bundle_dir, "dashboard.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "event_id": event_id,
            "summary": {
                "path_changes": len(diff.get("path_changes", [])),
                "schema_changes": len(diff.get("schema_changes", [])),
                "structured_changes": len(diff.get("structured_changes", [])),
            },
            "parser_risks": breakage,
            "signature_advisory": advisory,
        }, f, indent=2, sort_keys=True)
