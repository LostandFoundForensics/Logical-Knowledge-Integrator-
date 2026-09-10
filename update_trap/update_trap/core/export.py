"""
Update Trap — core/export.py
Packages a diff into a claim pack: snapshots, diff report (JSON + human
text + CSVs), parser rules, and Phase 3 parser-breakage/signature-advisory
files when a registry/signature library are supplied.

Fixes applied:
- claim_pack.json's created_utc now uses ISO 8601 (datetime.now(timezone.utc)
  .isoformat()) instead of a raw time.time() float, matching the timestamp
  convention used everywhere else in LoKi (LockBreaker, Witness Light, etc).
- event_id is now always present in claim_pack.json (UT_<unix-ts>), since
  downstream consumers (exhibits.py, claim_pack_importer.py, dashboard.py)
  all read claim.get("event_id") and previously had nothing to find.
- scope is now embedded into claim_pack.json (from the baseline snapshot),
  since claim_pack_importer.py and dashboard.py both read
  claim.get("scope", {}) but Phase 1/2's export() never wrote it.
"""
from __future__ import annotations

import os
import json
import csv
import time
from datetime import datetime, timezone
from dataclasses import asdict
from typing import Optional

from update_trap.core.models import Snapshot
from update_trap.core.diff_engine import DiffReport
from update_trap.core.rules_engine import RulesEngine
from update_trap.core.logbook import LogBook


class Exporter:
    def __init__(self, logbook: LogBook) -> None:
        self.logbook = logbook

    def export(
        self,
        outdir: str,
        base: Snapshot,
        new: Snapshot,
        report: DiffReport,
        registry_path: Optional[str] = None,
        signatures_dir: Optional[str] = None,
    ) -> str:
        os.makedirs(outdir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        bundle_dir = os.path.join(outdir, f"update_trap_claim_pack_{stamp}")
        os.makedirs(bundle_dir, exist_ok=True)

        base_path = os.path.join(bundle_dir, f"{base.label}.snapshot.json")
        new_path = os.path.join(bundle_dir, f"{new.label}.snapshot.json")
        base.save(base_path)
        new.save(new_path)

        report_json = {
            "baseline_label": report.baseline_label,
            "new_label": report.new_label,
            "path_changes": [asdict(pc) for pc in report.path_changes],
            "schema_changes": [asdict(sc) for sc in report.schema_changes],
            "structured_changes": [asdict(ch) for ch in report.structured_changes],
        }
        with open(os.path.join(bundle_dir, "diff_report.json"), "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2, sort_keys=True)

        with open(os.path.join(bundle_dir, "update_trap_report.txt"), "w", encoding="utf-8") as f:
            f.write(report.human_summary() + "\n")

        self._write_path_csv(bundle_dir, report)
        self._write_schema_csv(bundle_dir, report)
        self._write_structured_csv(bundle_dir, report)

        rules = RulesEngine().generate(report)
        with open(os.path.join(bundle_dir, "parser_rules.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "candidate_paths": rules.candidate_paths,
                    "column_maps": rules.column_maps,
                    "note": "Truth over convenience: column renames are not guessed.",
                },
                f,
                indent=2,
                sort_keys=True,
            )

        event_id = f"UT_{int(time.time())}"
        now_iso = datetime.now(timezone.utc).isoformat()

        claim_pack = {
            "tool": "Update Trap (LoKi)",
            "event_id": event_id,
            "created_utc": now_iso,
            "baseline_snapshot_file": os.path.basename(base_path),
            "new_snapshot_file": os.path.basename(new_path),
            "scope": {
                "source_profile": base.scope.source_profile,
                "targets": base.scope.targets,
                "structured_key_diff": base.scope.structured_key_diff,
            },
            "logbook": self.logbook.to_dict(),
            "observed_vs_inferred": {
                "observed": [
                    "file presence/absence",
                    "file hash changes",
                    "sqlite table/column diffs",
                    "structured (json/plist/xml) key diffs",
                ],
                "inferred": [
                    "candidate path suggestions (basename match only)",
                ],
            },
        }
        with open(os.path.join(bundle_dir, "claim_pack.json"), "w", encoding="utf-8") as f:
            json.dump(claim_pack, f, indent=2, sort_keys=True)

        # ── Phase 3: optional parser breakage + signature advisory ────────────
        if registry_path and os.path.exists(registry_path):
            try:
                from update_trap.core.breakage import ParserBreakageDetector
                detector = ParserBreakageDetector(registry_path)
                breakage = detector.analyze(report)
                with open(os.path.join(bundle_dir, "parser_breakage_assessment.json"), "w", encoding="utf-8") as f:
                    json.dump([b.to_dict() for b in breakage], f, indent=2, sort_keys=True)
                self.logbook.note(f"Parser breakage assessment written ({len(breakage)} finding(s)).")
            except Exception as e:
                self.logbook.note(f"WARNING: parser breakage assessment failed: {e}")

        if signatures_dir and os.path.isdir(signatures_dir):
            try:
                from update_trap.core.signatures import SignatureLibrary
                siglib = SignatureLibrary(signatures_dir)
                siglib.load()
                advisories = siglib.match(
                    base.scope.source_profile,
                    [pc.rel_path for pc in report.path_changes],
                )
                with open(os.path.join(bundle_dir, "signature_advisory.json"), "w", encoding="utf-8") as f:
                    json.dump(advisories, f, indent=2, sort_keys=True)
                self.logbook.note(f"Signature advisory written ({len(advisories)} match(es)).")
            except Exception as e:
                self.logbook.note(f"WARNING: signature advisory matching failed: {e}")

        self.logbook.note(f"Exported claim pack: {bundle_dir}")
        return bundle_dir

    def _write_path_csv(self, bundle_dir: str, report: DiffReport) -> None:
        path = os.path.join(bundle_dir, "path_changes.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["kind", "rel_path", "old_sha256", "new_sha256"])
            for pc in report.path_changes:
                w.writerow([pc.kind, pc.rel_path, pc.old_sha256 or "", pc.new_sha256 or ""])

    def _write_schema_csv(self, bundle_dir: str, report: DiffReport) -> None:
        path = os.path.join(bundle_dir, "schema_changes.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["db_rel_path", "table", "change", "details_json"])
            for sc in report.schema_changes:
                w.writerow([sc.db_rel_path, sc.table, sc.change, json.dumps(sc.details, sort_keys=True)])

    def _write_structured_csv(self, bundle_dir: str, report: DiffReport) -> None:
        path = os.path.join(bundle_dir, "structured_key_changes.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["rel_path", "kind", "change", "details_json"])
            for ch in report.structured_changes:
                w.writerow([ch.rel_path, ch.kind, ch.change, json.dumps(ch.details, sort_keys=True)])
