from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CasePaths:
    case_root: Path

    @property
    def evidence_nimbus(self) -> Path:
        return self.case_root / "evidence" / "nimbus"

    @property
    def work_nimbus(self) -> Path:
        return self.case_root / "work" / "nimbus"

    @property
    def loki_store(self) -> Path:
        return self.case_root / "loki" / "artifacts.sqlite"

    def nimbus_manifest_dir(self) -> Path:
        return self.evidence_nimbus / "manifests"

    def nimbus_manifest_path(self, import_id: str) -> Path:
        return self.nimbus_manifest_dir() / f"manifest_{import_id}.json"

    def nimbus_ledger_path(self) -> Path:
        return self.evidence_nimbus / "ledger" / "nimbus_ledger.ndjson"

    def takeout_work_dir(self, import_id: str) -> Path:
        return self.work_nimbus / "providers" / "google_takeout" / import_id

    def stage0_dir(self, import_id: str) -> Path:
        return self.work_nimbus / "intermediate" / f"stage0_{import_id}"

    def ensure_dirs(self) -> None:
        (self.evidence_nimbus / "raw_import").mkdir(parents=True, exist_ok=True)
        self.nimbus_manifest_dir().mkdir(parents=True, exist_ok=True)
        (self.evidence_nimbus / "ledger").mkdir(parents=True, exist_ok=True)
        (self.evidence_nimbus / "verification").mkdir(parents=True, exist_ok=True)
        (self.work_nimbus).mkdir(parents=True, exist_ok=True)
        (self.case_root / "exports" / "reports").mkdir(parents=True, exist_ok=True)
        (self.case_root / "loki").mkdir(parents=True, exist_ok=True)
        (self.case_root / "work" / "sundial").mkdir(parents=True, exist_ok=True)
        (self.case_root / "work" / "review").mkdir(parents=True, exist_ok=True)
        (self.case_root / "work" / "disclosure").mkdir(parents=True, exist_ok=True)
