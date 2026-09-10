from __future__ import annotations
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..models.enums import CopyPolicy, DatasetMode, IntakeState, SourceType, TruthState
from ..models.records import Dataset, IntakeRecord, TruthRecord
from ..storage.audit import AuditLog
from ..storage.store import DatasetStore, _sha256_file
from ..integrity.engine import IntegrityEngine

class QuarantineError(Exception):
    pass

class Actions:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.store = DatasetStore(self.root)
        self.audit = AuditLog(self.root / "logs" / "audit.log")
        self.integrity = IntegrityEngine(self.store, self.audit)

    def _utc_now(self): return datetime.now(timezone.utc).isoformat()

    def _check_not_quarantine(self):
        ds = self.store.load_dataset()
        if ds and ds.mode == DatasetMode.QUARANTINE:
            raise QuarantineError("Dataset is in QUARANTINE mode. This action is disabled.")

    def create_dataset(self, name, created_by, scope=None, artifact_families=None):
        ds = Dataset.new(name=name, created_by=created_by, scope=scope, artifact_families=artifact_families)
        self.store.save_dataset(ds)
        self.audit.append("CREATE_DATASET", {"dataset_id": ds.dataset_id, "name": name})
        return {"dataset_id": ds.dataset_id, "name": name, "created_utc": ds.created_utc}

    def _add_input(self, path, source_type, copy_policy=CopyPolicy.COPY_PRESERVE_TREE, notes="", audit_action="ADD_INPUT_FILE"):
        self._check_not_quarantine()
        rec = IntakeRecord.new(source_path=path, source_type=source_type, copy_policy=copy_policy, notes=notes)
        records = self.store.load_inputs_index()
        records.append(rec)
        self.store.save_inputs_index(records)
        self.audit.append(audit_action, {"intake_id": rec.intake_id, "path": path})
        return {"intake_id": rec.intake_id, "state": rec.state.value}

    def add_input_file(self, path, notes=""): return self._add_input(path, SourceType.GENERIC_FILES, notes=notes, audit_action="ADD_INPUT_FILE")
    def add_input_folder(self, path, copy_policy="copy_preserve_tree", notes=""): return self._add_input(path, SourceType.GENERIC_FILES, CopyPolicy(copy_policy), notes=notes, audit_action="ADD_INPUT_FOLDER")
    def add_ios_backup_folder(self, path, notes=""): return self._add_input(path, SourceType.IOS_BACKUP_FOLDER, notes=notes, audit_action="ADD_INPUT_IOS_BACKUP_FOLDER")
    def add_android_pull_folder(self, path, notes=""): return self._add_input(path, SourceType.ANDROID_PULL_FOLDER, notes=notes, audit_action="ADD_INPUT_ANDROID_PULL_FOLDER")

    def copy_inputs(self, intake_ids):
        self._check_not_quarantine()
        records = self.store.load_inputs_index()
        id_map = {r.intake_id: r for r in records}
        results = []
        for iid in intake_ids:
            rec = id_map.get(iid)
            if not rec: results.append({"intake_id": iid, "error": "not found"}); continue
            src = Path(rec.source_path)
            dest_root = self.root / "inputs" / "evidence" / rec.intake_id
            try:
                if src.is_file():
                    dest_root.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dest_root / src.name))
                    rec.bytes = src.stat().st_size
                elif src.is_dir():
                    if dest_root.exists(): shutil.rmtree(str(dest_root))
                    shutil.copytree(str(src), str(dest_root))
                    rec.bytes = sum(f.stat().st_size for f in dest_root.rglob("*") if f.is_file())
                else:
                    results.append({"intake_id": iid, "error": f"Source not found: {src}"}); continue
                rec.dataset_path = f"inputs/evidence/{rec.intake_id}/"
                rec.state = IntakeState.COPIED
                rec.copied_utc = self._utc_now()
                results.append({"intake_id": iid, "ok": True, "dataset_path": rec.dataset_path})
            except Exception as e:
                results.append({"intake_id": iid, "error": str(e)})
        self.store.save_inputs_index(records)
        self.audit.append("COPY_INPUTS", {"intake_ids": intake_ids, "results": results})
        return {"results": results}

    def exclude_inputs(self, intake_ids):
        self._check_not_quarantine()
        records = self.store.load_inputs_index()
        excluded = []
        for rec in records:
            if rec.intake_id in intake_ids:
                rec.state = IntakeState.EXCLUDED
                rec.excluded_utc = self._utc_now()
                excluded.append(rec.intake_id)
        self.store.save_inputs_index(records)
        self.audit.append("EXCLUDE_INPUTS", {"excluded": excluded})
        return {"excluded": excluded}

    def hash_inputs(self, intake_ids):
        records = self.store.load_inputs_index()
        id_map = {r.intake_id: r for r in records}
        hashes = self.store.load_hashes()
        prev_manifest_hash = self.store.hash_manifest_json()
        results = []
        for iid in intake_ids:
            rec = id_map.get(iid)
            if not rec: results.append({"intake_id": iid, "error": "not found"}); continue
            if rec.state.value in ("staged","excluded"): results.append({"intake_id": iid, "error": f"Cannot hash in state {rec.state.value}"}); continue
            if not rec.dataset_path: results.append({"intake_id": iid, "error": "No dataset copy to hash"}); continue
            dataset_copy = self.root / rec.dataset_path
            if not dataset_copy.exists(): results.append({"intake_id": iid, "error": f"Missing: {rec.dataset_path}"}); continue
            try:
                sha = _sha256_file(dataset_copy) if dataset_copy.is_file() else self.store.compute_dir_hash(dataset_copy)
                rec.hash.sha256 = sha; rec.state = IntakeState.HASHED; rec.hashed_utc = self._utc_now()
                hashes.setdefault("inputs", {})[rec.dataset_path] = sha
                results.append({"intake_id": iid, "sha256": sha})
            except Exception as e:
                results.append({"intake_id": iid, "error": str(e)})
        self.store.save_inputs_index(records)
        self.store.save_hashes(hashes)
        self.store.append_manifest_history(prev_manifest_hash, hashes)
        self.audit.append("HASH_INPUTS", {"intake_ids": intake_ids, "results": results})
        return {"results": results}

    def _integrity_result_dict(self, result):
        return {"ok": result.ok, "failures": [{"type": f.failure_type, "detail": f.detail, "intake_id": f.intake_id} for f in result.failures]}

    def verify_evidence_integrity(self, intake_ids=None):
        result = self.integrity.verify_evidence(intake_ids)
        self.audit.append("VERIFY_EVIDENCE_INTEGRITY", {"ok": result.ok, "failures": len(result.failures)})
        if not result.ok: self.store.set_quarantine(reason=f"Evidence integrity failure")
        return self._integrity_result_dict(result)

    def verify_dataset_integrity(self):
        result = self.integrity.verify_dataset_full()
        self.audit.append("VERIFY_DATASET_INTEGRITY", {"ok": result.ok, "failures": len(result.failures)})
        if not result.ok: self.store.set_quarantine(reason="Dataset integrity failure")
        return self._integrity_result_dict(result)

    def export_integrity_failure_report(self, run_id):
        result = self.integrity.verify_dataset_full()
        out_path = self.root / "runs" / run_id / "integrity_failure_report.json"
        self.integrity.export_failure_report(result, out_path)
        self.audit.append("EXPORT_INTEGRITY_FAILURE_REPORT", {"run_id": run_id, "path": str(out_path)})
        return {"path": str(out_path), "ok": result.ok, "failures": len(result.failures)}

    def add_truth_record(self, record):
        records = self.store.load_truth_ledger()
        records.append(record)
        self.store.save_truth_ledger(records)
        self.audit.append("ADD_TRUTH_RECORD", {"record_id": record.record_id, "artifact_type": record.artifact_type.value, "timestamp.value": record.timestamp.value})
        return {"record_id": record.record_id, "state": record.state.value}

    def approve_truth(self, record_id, approved_by):
        records = self.store.load_truth_ledger()
        for rec in records:
            if rec.record_id == record_id:
                rec.approve(approved_by)
                self.store.save_truth_ledger(records)
                self.audit.append("APPROVE_TRUTH", {"record_id": record_id, "artifact_type": rec.artifact_type.value, "timestamp.value": rec.timestamp.value})
                return {"record_id": record_id, "state": rec.state.value}
        raise ValueError(f"Record not found: {record_id}")

    def revoke_truth(self, record_id):
        records = self.store.load_truth_ledger()
        for rec in records:
            if rec.record_id == record_id:
                rec.revoke()
                self.store.save_truth_ledger(records)
                self.audit.append("REVOKE_TRUTH", {"record_id": record_id})
                return {"record_id": record_id, "state": rec.state.value}
        raise ValueError(f"Record not found: {record_id}")

    def delete_draft_truth(self, record_id):
        records = self.store.load_truth_ledger()
        to_del = next((r for r in records if r.record_id == record_id), None)
        if not to_del: raise ValueError(f"Record not found: {record_id}")
        if to_del.state != TruthState.DRAFT_TRUTH: raise ValueError("Only draft truth records can be deleted")
        records = [r for r in records if r.record_id != record_id]
        self.store.save_truth_ledger(records)
        self.audit.append("DELETE_DRAFT_TRUTH", {"record_id": record_id})
        return {"deleted": record_id}

    def verify_ledger_integrity(self):
        result = self.integrity.verify_truth_ledger()
        self.audit.append("VERIFY_LEDGER_INTEGRITY", {"ok": result.ok})
        return self._integrity_result_dict(result)

    def get_audit_log(self): return self.audit.read_all()

    def get_truth_ledger(self):
        return [{"record_id": r.record_id, "state": r.state.value, "artifact_type": r.artifact_type.value,
                 "timestamp": {"value": r.timestamp.value, "timezone": r.timestamp.timezone},
                 "participants": [{"id": p.id, "label": p.label} for p in r.participants],
                 "confidence": r.confidence.value, "direction": r.direction, "content": r.content,
                 "source": {"method": r.source.method.value, "reference": r.source.reference},
                 "assertion": {"asserted_by": r.assertion.asserted_by, "approved_by": r.assertion.approved_by, "approved_utc": r.assertion.approved_utc},
                 "notes": r.notes} for r in self.store.load_truth_ledger()]

    def get_inputs_index(self):
        return [{"intake_id": r.intake_id, "state": r.state.value, "source_type": r.source_type.value,
                 "source_path": r.source_path, "copy_policy": r.copy_policy.value, "dataset_path": r.dataset_path,
                 "bytes": r.bytes, "hash": {"sha256": r.hash.sha256}, "added_utc": r.added_utc,
                 "copied_utc": r.copied_utc, "hashed_utc": r.hashed_utc, "excluded_utc": r.excluded_utc, "notes": r.notes}
                for r in self.store.load_inputs_index()]

    def get_dataset_status(self):
        ds = self.store.load_dataset()
        if not ds: return {"error": "No dataset found"}
        records = self.store.load_truth_ledger()
        draft = sum(1 for r in records if r.state == TruthState.DRAFT_TRUTH)
        return {"dataset_id": ds.dataset_id, "name": ds.name, "mode": ds.mode.value, "status": ds.status,
                "created_by": ds.created_by, "created_utc": ds.created_utc,
                "draft_truth_count": draft, "observed_truth_count": len(records) - draft}
