from __future__ import annotations
import hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..models.enums import ArtifactType, Confidence, CopyPolicy, DatasetMode, IntakeState, SourceMethod, SourceType, TruthState
from ..models.records import Assertion, Dataset, IntakeHash, IntakeRecord, Participant, Source, Timestamp, TruthRecord

def _utc_now(): return datetime.now(timezone.utc).isoformat()

def _write_json_atomic(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    shutil.move(str(tmp), str(path))

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def _sha256_dir(dir_path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(dir_path.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(dir_path)).replace("\\", "/")
            h.update(rel.encode("utf-8"))
            h.update(_sha256_file(p).encode("utf-8"))
    return h.hexdigest()

class DatasetStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in ["truth", "inputs/evidence", "runs", "manifest", "logs"]:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def load_dataset(self) -> Optional[Dataset]:
        p = self.root / "dataset.json"
        if not p.exists(): return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return Dataset(dataset_id=d["dataset_id"], name=d["name"], created_utc=d["created_utc"],
                       created_by=d["created_by"], loki_schema_version=d.get("loki_schema_version","1.0"),
                       truthloom_version=d.get("truthloom_version","0.1"), scope=d.get("scope",[]),
                       artifact_families=d.get("artifact_families",[]), status=d.get("status","draft"),
                       mode=DatasetMode(d.get("mode","normal")))

    def save_dataset(self, ds: Dataset):
        _write_json_atomic(self.root / "dataset.json", {
            "dataset_id": ds.dataset_id, "name": ds.name, "created_utc": ds.created_utc,
            "created_by": ds.created_by, "loki_schema_version": ds.loki_schema_version,
            "truthloom_version": ds.truthloom_version, "scope": ds.scope,
            "artifact_families": ds.artifact_families, "status": ds.status, "mode": ds.mode.value})

    def set_quarantine(self, reason: str):
        ds = self.load_dataset()
        if ds:
            ds.mode = DatasetMode.QUARANTINE
            self.save_dataset(ds)
        alert_path = self.root / "logs" / "integrity_alert.log"
        with alert_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp_utc": _utc_now(), "reason": reason}) + "\n")

    def load_truth_ledger(self) -> List[TruthRecord]:
        p = self.root / "truth" / "truth_ledger.json"
        if not p.exists(): return []
        data = json.loads(p.read_text(encoding="utf-8"))
        records = []
        for r in data.get("records", []):
            ts = r["timestamp"]; src = r.get("source",{}); asrt = r.get("assertion",{})
            records.append(TruthRecord(
                record_id=r["record_id"], state=TruthState(r["state"]),
                artifact_type=ArtifactType(r["artifact_type"]),
                timestamp=Timestamp(value=ts["value"], timezone=ts["timezone"]),
                participants=[Participant(id=pp["id"], label=pp["label"]) for pp in r.get("participants",[])],
                confidence=Confidence(r.get("confidence","certain")),
                source=Source(method=SourceMethod(src.get("method","manual_entry")), reference=src.get("reference")),
                assertion=Assertion(asserted_by=asrt.get("asserted_by"), asserted_utc=asrt.get("asserted_utc"),
                                    approved_by=asrt.get("approved_by"), approved_utc=asrt.get("approved_utc")),
                direction=r.get("direction"), content=r.get("content"),
                attachments=r.get("attachments",[]), notes=r.get("notes","")))
        return records

    def save_truth_ledger(self, records: List[TruthRecord]):
        def _rec(r):
            return {"record_id": r.record_id, "state": r.state.value,
                    "artifact_type": r.artifact_type.value,
                    "timestamp": {"value": r.timestamp.value, "timezone": r.timestamp.timezone},
                    "participants": [{"id": p.id, "label": p.label} for p in r.participants],
                    "confidence": r.confidence.value,
                    "source": {"method": r.source.method.value, "reference": r.source.reference},
                    "assertion": {"asserted_by": r.assertion.asserted_by, "asserted_utc": r.assertion.asserted_utc,
                                  "approved_by": r.assertion.approved_by, "approved_utc": r.assertion.approved_utc},
                    "direction": r.direction, "content": r.content, "attachments": r.attachments, "notes": r.notes}
        _write_json_atomic(self.root / "truth" / "truth_ledger.json",
                           {"ledger_version":"1.0","generated_utc":_utc_now(),"records":[_rec(r) for r in records]})

    def load_inputs_index(self) -> List[IntakeRecord]:
        p = self.root / "inputs" / "inputs_index.json"
        if not p.exists(): return []
        data = json.loads(p.read_text(encoding="utf-8"))
        return [IntakeRecord(intake_id=r["intake_id"], state=IntakeState(r["state"]),
                             source_type=SourceType(r["source_type"]), source_path=r["source_path"],
                             copy_policy=CopyPolicy(r["copy_policy"]), dataset_path=r.get("dataset_path"),
                             bytes=r.get("bytes"), hash=IntakeHash(sha256=r.get("hash",{}).get("sha256")),
                             added_utc=r["added_utc"], copied_utc=r.get("copied_utc"),
                             hashed_utc=r.get("hashed_utc"), excluded_utc=r.get("excluded_utc"),
                             notes=r.get("notes","")) for r in data.get("records",[])]

    def save_inputs_index(self, records: List[IntakeRecord]):
        def _rec(r):
            return {"intake_id": r.intake_id, "state": r.state.value, "source_type": r.source_type.value,
                    "source_path": r.source_path, "copy_policy": r.copy_policy.value,
                    "dataset_path": r.dataset_path, "bytes": r.bytes, "hash": {"sha256": r.hash.sha256},
                    "added_utc": r.added_utc, "copied_utc": r.copied_utc, "hashed_utc": r.hashed_utc,
                    "excluded_utc": r.excluded_utc, "notes": r.notes}
        _write_json_atomic(self.root / "inputs" / "inputs_index.json",
                           {"inputs_version":"1.0","generated_utc":_utc_now(),"records":[_rec(r) for r in records]})

    def load_hashes(self) -> Dict[str, Any]:
        p = self.root / "manifest" / "hashes.json"
        if not p.exists(): return {"inputs":{},"truth":{},"runs":{},"reports":{}}
        return json.loads(p.read_text(encoding="utf-8"))

    def save_hashes(self, hashes: Dict[str, Any]):
        _write_json_atomic(self.root / "manifest" / "hashes.json", hashes)

    def append_manifest_history(self, prev_manifest_hash: str, new_hashes: Dict[str, Any]):
        p = self.root / "manifest" / "manifest_history.jsonl"
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp_utc":_utc_now(),"prev_manifest_hash":prev_manifest_hash,"hashes_snapshot":new_hashes},ensure_ascii=False)+"\n")

    def compute_file_hash(self, path: Path) -> str: return _sha256_file(path)
    def compute_dir_hash(self, path: Path) -> str: return _sha256_dir(path)
    def hash_manifest_json(self) -> str:
        p = self.root / "manifest" / "hashes.json"
        return _sha256_file(p) if p.exists() else ""
