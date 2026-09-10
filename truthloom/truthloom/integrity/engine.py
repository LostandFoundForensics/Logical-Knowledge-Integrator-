from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from ..storage.store import DatasetStore, _sha256_file

@dataclass
class IntegrityFailure:
    failure_type: str
    intake_id: Optional[str] = None
    path: Optional[str] = None
    detail: str = ""

@dataclass
class IntegrityResult:
    ok: bool
    failures: List[IntegrityFailure] = field(default_factory=list)
    def add(self, failure_type, detail="", intake_id=None, path=None):
        self.failures.append(IntegrityFailure(failure_type=failure_type, detail=detail, intake_id=intake_id, path=path))
        self.ok = False

class IntegrityEngine:
    def __init__(self, store: DatasetStore, audit):
        self.store = store
        self.audit = audit

    def verify_evidence(self, intake_ids=None) -> IntegrityResult:
        result = IntegrityResult(ok=True)
        for rec in self.store.load_inputs_index():
            if intake_ids is not None and rec.intake_id not in intake_ids: continue
            if rec.state.value in ("staged", "excluded") or rec.hash.sha256 is None: continue
            if not rec.dataset_path:
                result.add("missing_evidence_file", intake_id=rec.intake_id, detail="dataset_path is None"); continue
            dataset_copy = self.store.root / rec.dataset_path
            if not dataset_copy.exists():
                result.add("missing_evidence_file", intake_id=rec.intake_id, path=str(dataset_copy),
                           detail=f"Dataset copy missing: {rec.dataset_path}"); continue
            computed = _sha256_file(dataset_copy) if dataset_copy.is_file() else self.store.compute_dir_hash(dataset_copy)
            if computed != rec.hash.sha256:
                result.add("evidence_hash_mismatch", intake_id=rec.intake_id, path=str(dataset_copy),
                           detail=f"Expected {rec.hash.sha256[:12]} got {computed[:12]}")
        return result

    def verify_truth_ledger(self) -> IntegrityResult:
        result = IntegrityResult(ok=True)
        hashes = self.store.load_hashes()
        ledger_path = self.store.root / "truth" / "truth_ledger.json"
        if not ledger_path.exists() or "truth_ledger.json" not in hashes.get("truth", {}): return result
        stored = hashes["truth"]["truth_ledger.json"]
        computed = _sha256_file(ledger_path)
        if computed != stored:
            result.add("truth_ledger_hash_mismatch", path=str(ledger_path),
                       detail=f"Expected {stored[:12]} got {computed[:12]}")
        return result

    def verify_audit_chain(self) -> IntegrityResult:
        result = IntegrityResult(ok=True)
        ok, errors = self.audit.verify_chain()
        if not ok:
            for e in errors: result.add("audit_chain_invalid", detail=e)
        return result

    def verify_manifest_history(self) -> IntegrityResult:
        result = IntegrityResult(ok=True)
        p = self.store.root / "manifest" / "manifest_history.jsonl"
        if not p.exists(): return result
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line: continue
            try:
                entry = json.loads(line)
                if i > 0 and not entry.get("prev_manifest_hash"):
                    result.add("manifest_chain_invalid", detail=f"Entry {i} missing prev_manifest_hash")
            except json.JSONDecodeError as e:
                result.add("manifest_chain_invalid", detail=f"Unparseable line: {e}")
        return result

    def verify_dataset_full(self) -> IntegrityResult:
        combined = IntegrityResult(ok=True)
        for sub in [self.verify_evidence(), self.verify_truth_ledger(), self.verify_audit_chain(), self.verify_manifest_history()]:
            if not sub.ok:
                combined.ok = False
                combined.failures.extend(sub.failures)
        return combined

    def export_failure_report(self, result: IntegrityResult, output_path: Path) -> Path:
        import datetime
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "ok": result.ok, "failure_count": len(result.failures),
                  "failures": [{"failure_type": f.failure_type, "intake_id": f.intake_id,
                                 "path": f.path, "detail": f.detail} for f in result.failures]}
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path
