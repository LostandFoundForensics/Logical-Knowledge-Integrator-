"""
Sundial — Case Bundle Loader
Phase 1: Open whatever it is given. Everything except case.json is optional.

A reader should never refuse to load. If loki_normalized.db is missing, Sundial
shows the case shell and reports what's absent — it does not error out.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sundial.core.schema import ALL_SCHEMA, SCHEMA_VERSION


@dataclass
class BundleStatus:
    """What Sundial found when it opened a bundle. Absence is reported, not hidden."""
    case_present: bool
    db_present: bool
    artifacts_present: bool
    acquisition_log_present: bool
    parser_log_present: bool
    hash_manifest_present: bool
    schema_version: Optional[str]
    missing: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class CaseInfo:
    case_id: str
    case_name: str
    created_utc: str
    owner_label: str
    device_label: str
    notes: str = ""
    schema_version: str = SCHEMA_VERSION


class CaseBundle:
    """
    Represents an opened case bundle. Holds a read-only connection to the
    normalized DB when present, and a clear status of what's available.
    """

    def __init__(self, bundle_dir: str):
        self.bundle_dir = Path(bundle_dir).expanduser().resolve()
        self.case_info: Optional[CaseInfo] = None
        self.status: Optional[BundleStatus] = None
        self._conn: Optional[sqlite3.Connection] = None

    # ── Open ──────────────────────────────────────────────────────────────────
    def open(self) -> BundleStatus:
        missing: List[str] = []
        notes: List[str] = []

        case_json = self.bundle_dir / "case.json"
        case_present = case_json.exists()
        if not case_present:
            missing.append("case.json")
            notes.append("No case.json found. This is the one required file.")
        else:
            self.case_info = self._load_case_info(case_json)

        db_path = self.bundle_dir / "loki_normalized.db"
        db_present = db_path.exists()
        schema_version: Optional[str] = None

        if db_present:
            self._conn = sqlite3.connect(
                f"file:{db_path.as_posix()}?mode=ro",
                uri=True,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            schema_version = self._read_schema_version()
            if schema_version is None:
                notes.append(
                    "Database present but has no schema_version. "
                    "Treating as legacy; some Phase 3 features may be unavailable."
                )
        else:
            missing.append("loki_normalized.db")
            notes.append(
                "No normalized database in this bundle. The case can be opened, "
                "but there is no timeline to display yet."
            )

        artifacts_present = (self.bundle_dir / "artifacts").is_dir()
        acq_log = (self.bundle_dir / "logs" / "acquisition.log").exists()
        parser_log = (self.bundle_dir / "logs" / "parser.log").exists()
        hash_manifest = (self.bundle_dir / "ledger" / "hashes.manifest.txt").exists()

        self.status = BundleStatus(
            case_present=case_present,
            db_present=db_present,
            artifacts_present=artifacts_present,
            acquisition_log_present=acq_log,
            parser_log_present=parser_log,
            hash_manifest_present=hash_manifest,
            schema_version=schema_version,
            missing=missing,
            notes=notes,
        )
        return self.status

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _load_case_info(self, case_json: Path) -> Optional[CaseInfo]:
        try:
            data = json.loads(case_json.read_text(encoding="utf-8"))
        except Exception:
            return None
        return CaseInfo(
            case_id=str(data.get("case_id", "")),
            case_name=str(data.get("case_name", "Untitled Case")),
            created_utc=str(data.get("created_utc", "")),
            owner_label=str(data.get("owner_label", "")),
            device_label=str(data.get("device_label", "")),
            notes=str(data.get("notes", "")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )

    def _read_schema_version(self) -> Optional[str]:
        if self._conn is None:
            return None
        try:
            cur = self._conn.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            )
            row = cur.fetchone()
            return row["value"] if row else None
        except sqlite3.Error:
            return None  # meta table may not exist in legacy bundles

    @property
    def conn(self) -> Optional[sqlite3.Connection]:
        return self._conn

    def has_table(self, name: str) -> bool:
        if self._conn is None:
            return False
        cur = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return cur.fetchone() is not None

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


def init_empty_db(db_path: str) -> None:
    """
    Create a fresh, schema-complete Sundial DB. Used for tests / demo data and
    by any upstream tool that wants to write a Sundial-ready bundle.
    """
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    try:
        for stmt in ALL_SCHEMA:
            conn.executescript(stmt)
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        conn.commit()
    finally:
        conn.close()
