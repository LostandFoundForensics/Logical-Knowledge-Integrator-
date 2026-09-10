"""
Update Trap — core/exhibits.py
Produces court-safe exhibits from an Update Trap claim pack folder:
  1. Plain-language impact summary
  2. Technical appendix
  3. Change tables (CSV)
  4. Attachments index (CSV, with SHA-256 of every file in the pack)
"""
from __future__ import annotations

import os
import json
import csv
import time
import hashlib
from typing import Any, Dict


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def generate_exhibit_pack(claim_pack_dir: str) -> str:
    """
    Produces court-safe exhibits from an Update Trap claim pack folder.
    Output is written into claim_pack_dir/exhibits_<timestamp>/
    """
    required = ["claim_pack.json", "diff_report.json", "parser_rules.json"]
    for fn in required:
        p = os.path.join(claim_pack_dir, fn)
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing required file: {fn}")

    def read_json(name: str) -> Any:
        p = os.path.join(claim_pack_dir, name)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    claim = read_json("claim_pack.json") or {}
    diff = read_json("diff_report.json") or {}
    rules = read_json("parser_rules.json") or {}
    breakage = read_json("parser_breakage_assessment.json")
    advisory = read_json("signature_advisory.json")
    dashboard = read_json("dashboard.json")
    approved_patch = read_json("approved_patch.json")
    validation = read_json("validation_event.json")

    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    outdir = os.path.join(claim_pack_dir, f"exhibits_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    exhibit01 = build_exhibit_01_plain(claim, diff, breakage, advisory, approved_patch, validation)
    write_text(os.path.join(outdir, "EXHIBIT_01_Update_Impact_Summary.txt"), exhibit01)

    exhibit02 = build_exhibit_02_technical(claim, diff, rules, breakage, advisory, dashboard)
    write_text(os.path.join(outdir, "EXHIBIT_02_Technical_Appendix.txt"), exhibit02)

    write_change_tables(outdir, diff)
    write_attachments_index(outdir, claim_pack_dir)

    pack = {
        "tool": "Update Trap (LoKi) — Exhibit Generator",
        "created_utc": time.time(),
        "source_claim_pack_dir": os.path.abspath(claim_pack_dir),
        "outputs": {
            "exhibit_01": "EXHIBIT_01_Update_Impact_Summary.txt",
            "exhibit_02": "EXHIBIT_02_Technical_Appendix.txt",
            "exhibit_03_csv": "EXHIBIT_03_Change_Tables.csv",
            "exhibit_04_csv": "EXHIBIT_04_Attachments_Index.csv",
        },
        "observed_vs_inferred_policy": {
            "observed": ["hashes", "file presence/absence", "file hash changes", "sqlite schema diffs", "structured-key diffs"],
            "inferred": ["candidate path suggestions", "signature advisory correlation", "parser risk assessment"],
        },
    }
    with open(os.path.join(outdir, "exhibit_pack.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, sort_keys=True)

    return outdir


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def build_exhibit_01_plain(
    claim: dict, diff: dict, breakage: Any, advisory: Any, approved_patch: Any, validation: Any
) -> str:
    event_id = claim.get("event_id", "unknown_event")
    baseline = diff.get("baseline_label", "baseline")
    new = diff.get("new_label", "new")

    path_changes = diff.get("path_changes", [])
    schema_changes = diff.get("schema_changes", [])
    structured_changes = diff.get("structured_changes", [])

    lines = []
    lines.append("EXHIBIT 01 — UPDATE IMPACT SUMMARY (PLAIN LANGUAGE)")
    lines.append("")
    lines.append(f"Update Event ID: {event_id}")
    lines.append(f"Compared Snapshots: {baseline} → {new}")
    lines.append("")
    lines.append("1) WHAT WAS COMPARED")
    lines.append("We compared two snapshots of device data collected at two different times (a baseline and a newer snapshot).")
    lines.append("The purpose was to determine whether an operating system or application update changed where records are stored or how they are structured.")
    lines.append("")
    lines.append("2) WHAT CHANGED (OBSERVED)")
    lines.append(f"- File/path changes observed: {len(path_changes)}")
    lines.append(f"- Database schema changes observed: {len(schema_changes)}")
    lines.append(f"- Structured data key-layout changes observed: {len(structured_changes)}")
    lines.append("")
    lines.append("Examples (observed):")
    for pc in path_changes[:5]:
        lines.append(f"  - {pc.get('kind', 'change')}: {pc.get('rel_path', '(unknown)')}")
    if len(path_changes) > 5:
        lines.append("  - (additional changes listed in Exhibit 03)")
    lines.append("")
    lines.append("3) WHY THIS MATTERS")
    lines.append("If updates move files or alter database structures, forensic tools can fail to locate records or may interpret fields incorrectly until updated.")
    lines.append("")
    lines.append("4) WHAT THIS TOOL DID NOT DO")
    lines.append("- It did not modify evidence.")
    lines.append("- It did not automatically update or rewrite forensic parsers.")
    lines.append("- It did not guess column renames or fabricate missing data.")
    lines.append("")
    lines.append("5) INFERENCES (LABELED)")
    if breakage:
        lines.append("Parser Risk Assessment (inferred):")
        for f in breakage[:5]:
            lines.append(f"  - {f.get('parser_id')} risk={f.get('risk_level')}")
    else:
        lines.append("No parser risk assessment file was present in this exhibit pack.")
    if advisory:
        lines.append("")
        lines.append("Signature Advisory (inferred, non-deterministic):")
        for a in advisory[:3]:
            lines.append(f"  - {a.get('id', '(unknown)')} (matched_patterns={a.get('matched_patterns', 0)})")
    lines.append("")
    lines.append("6) LIMITATIONS")
    lines.append("This exhibit reports changes that were detected within the provided snapshot scope. Items outside scope are not evaluated.")
    lines.append("")
    lines.append("7) ACTIONS TAKEN (IF PRESENT)")
    if approved_patch:
        lines.append("- An approved parser patch file was included (config-only).")
    if validation:
        lines.append("- A validation event file was included indicating a verification run against known truth.")
    if not approved_patch and not validation:
        lines.append("- No approved patch or validation record was included in this exhibit pack.")
    lines.append("")
    lines.append("See Exhibit 02 (Technical Appendix) and Exhibit 03 (Change Tables) for full detail.")
    return "\n".join(lines)


def build_exhibit_02_technical(
    claim: dict, diff: dict, rules: dict, breakage: Any, advisory: Any, dashboard: Any
) -> str:
    lines = []
    lines.append("EXHIBIT 02 — TECHNICAL APPENDIX")
    lines.append("")
    lines.append("A) PROVENANCE")
    lines.append(f"Tool: {claim.get('tool', 'Update Trap (LoKi)')}")
    lines.append(f"Created UTC: {claim.get('created_utc', '(unknown)')}")
    lines.append("")
    lines.append("B) DIFF SUMMARY (OBSERVED)")
    lines.append(f"- Path changes: {len(diff.get('path_changes', []))}")
    lines.append(f"- Schema changes: {len(diff.get('schema_changes', []))}")
    lines.append(f"- Structured-key changes: {len(diff.get('structured_changes', []))}")
    lines.append("")
    lines.append("C) PARSER RULES (INFERRED SUGGESTIONS)")
    cand = rules.get("candidate_paths", {})
    lines.append(f"- Candidate path suggestion entries: {len(cand)}")
    lines.append("Note: Candidate paths are suggestions only and must be confirmed by a human.")
    lines.append("")
    lines.append("D) PARSER RISK ASSESSMENT (INFERRED)")
    if breakage:
        lines.append(f"- Parsers flagged: {len(breakage)}")
        for f in breakage[:10]:
            lines.append(f"  - {f.get('parser_id')} risk={f.get('risk_level')} reasons={len(f.get('reasons', []))}")
    else:
        lines.append("- (no parser_breakage_assessment.json present)")
    lines.append("")
    lines.append("E) SIGNATURE ADVISORY (INFERRED, NON-DETERMINISTIC)")
    if advisory:
        for a in advisory[:10]:
            lines.append(f"  - {a.get('id', '(unknown)')} matched_patterns={a.get('matched_patterns', 0)}")
    else:
        lines.append("- (no signature_advisory.json present)")
    lines.append("")
    lines.append("F) DASHBOARD (IF PRESENT)")
    if dashboard:
        lines.append(f"- Event: {dashboard.get('event_id', '(unknown)')}")
        lines.append(f"- Summary: {dashboard.get('summary', {})}")
    else:
        lines.append("- (no dashboard.json present)")
    lines.append("")
    lines.append("Full change details are provided in Exhibit 03.")
    return "\n".join(lines)


def write_change_tables(outdir: str, diff: dict) -> None:
    path = os.path.join(outdir, "EXHIBIT_03_Change_Tables.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "primary", "change", "details_json"])

        for pc in diff.get("path_changes", []):
            w.writerow([
                "path", pc.get("rel_path", ""), pc.get("kind", ""),
                json.dumps({"old": pc.get("old_sha256"), "new": pc.get("new_sha256")}, sort_keys=True),
            ])

        for sc in diff.get("schema_changes", []):
            w.writerow([
                "schema", f"{sc.get('db_rel_path', '')}::{sc.get('table', '')}", sc.get("change", ""),
                json.dumps(sc.get("details", {}), sort_keys=True),
            ])

        for ch in diff.get("structured_changes", []):
            w.writerow([
                "structured", ch.get("rel_path", ""), ch.get("change", ""),
                json.dumps(ch.get("details", {}), sort_keys=True),
            ])


def write_attachments_index(outdir: str, claim_pack_dir: str) -> None:
    idx_path = os.path.join(outdir, "EXHIBIT_04_Attachments_Index.csv")
    with open(idx_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "sha256", "role_notes"])

        for fn in sorted(os.listdir(claim_pack_dir)):
            p = os.path.join(claim_pack_dir, fn)
            if os.path.isdir(p):
                continue
            try:
                h = sha256_file(p)
            except Exception:
                h = "(hash_failed)"
            note = role_note(fn)
            w.writerow([fn, h, note])


def role_note(fn: str) -> str:
    m = {
        "claim_pack.json": "Provenance + observed vs inferred policy",
        "diff_report.json": "Observed diff results (paths/schemas/keys)",
        "schema_changes.csv": "Observed schema changes (tabular)",
        "path_changes.csv": "Observed file changes (tabular)",
        "structured_key_changes.csv": "Observed structured-key changes (tabular)",
        "parser_rules.json": "Inferred suggestions (candidate paths / TODO maps)",
        "parser_breakage_assessment.json": "Inferred parser risk assessment",
        "signature_advisory.json": "Inferred signature correlations (non-deterministic)",
        "dashboard.json": "Summary dashboard data",
    }
    return m.get(fn, "")
