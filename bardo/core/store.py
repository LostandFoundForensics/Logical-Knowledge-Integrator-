"""
Working case store — SQLite we create and own.

Never open evidence DBs through this module for writes.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from bardo.core.models import Observation, Entity


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
  obs_id TEXT PRIMARY KEY,
  source_tool TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  timestamp_unix_ms INTEGER,
  timestamp_label TEXT,
  entities_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL DEFAULT '{}',
  provenance_path TEXT,
  confidence REAL,
  flags_json TEXT NOT NULL DEFAULT '[]',
  ingested_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  first_seen_obs TEXT,
  obs_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(timestamp_unix_ms);
CREATE INDEX IF NOT EXISTS idx_obs_type ON observations(artifact_type);
CREATE INDEX IF NOT EXISTS idx_obs_tool ON observations(source_tool);
CREATE INDEX IF NOT EXISTS idx_ent_value ON entities(value);
"""


class CaseStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def __enter__(self) -> "CaseStore":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def get_meta(self, key: str, default: str = "") -> str:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def upsert_observation(self, obs: Observation) -> None:
        self.conn.execute(
            """
            INSERT INTO observations(
              obs_id, source_tool, artifact_type, summary,
              timestamp_unix_ms, timestamp_label, entities_json,
              payload_json, provenance_path, confidence, flags_json, ingested_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(obs_id) DO UPDATE SET
              summary=excluded.summary,
              timestamp_unix_ms=excluded.timestamp_unix_ms,
              entities_json=excluded.entities_json,
              payload_json=excluded.payload_json,
              confidence=excluded.confidence
            """,
            (
                obs.obs_id,
                obs.source_tool,
                obs.artifact_type,
                obs.summary,
                obs.timestamp_unix_ms,
                obs.timestamp_label,
                json.dumps(obs.entities),
                json.dumps(obs.payload),
                obs.provenance_path,
                obs.confidence,
                json.dumps(obs.flags),
                int(time.time()),
            ),
        )
        for val in obs.entities:
            self._touch_entity(val, obs.obs_id)
        self.conn.commit()

    def _touch_entity(self, value: str, obs_id: str) -> None:
        value = (value or "").strip()
        if not value:
            return
        kind = "phone" if value.startswith("+") or value.isdigit() else "other"
        if "@" in value:
            kind = "email"
        eid = f"{kind}:{value.lower()}"
        row = self.conn.execute(
            "SELECT obs_count FROM entities WHERE entity_id=?", (eid,)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE entities SET obs_count = obs_count + 1 WHERE entity_id=?",
                (eid,),
            )
        else:
            self.conn.execute(
                "INSERT INTO entities(entity_id, kind, value, first_seen_obs, obs_count) "
                "VALUES (?,?,?,?,1)",
                (eid, kind, value, obs_id),
            )

    def summary(self) -> Dict[str, Any]:
        def count(table: str) -> int:
            return int(
                self.conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
            )

        by_type = {
            r["artifact_type"]: r["c"]
            for r in self.conn.execute(
                "SELECT artifact_type, COUNT(*) AS c FROM observations "
                "GROUP BY artifact_type ORDER BY c DESC"
            )
        }
        by_tool = {
            r["source_tool"]: r["c"]
            for r in self.conn.execute(
                "SELECT source_tool, COUNT(*) AS c FROM observations "
                "GROUP BY source_tool"
            )
        }
        return {
            "path": str(self.path),
            "observations": count("observations"),
            "entities": count("entities"),
            "by_type": by_type,
            "by_tool": by_tool,
            "case_id": self.get_meta("case_id"),
        }

    def list_observations(
        self,
        *,
        limit: int = 1000,
        artifact_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if artifact_type:
            rows = self.conn.execute(
                "SELECT * FROM observations WHERE artifact_type=? "
                "ORDER BY timestamp_unix_ms IS NULL, timestamp_unix_ms LIMIT ?",
                (artifact_type, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM observations "
                "ORDER BY timestamp_unix_ms IS NULL, timestamp_unix_ms LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            out.append({
                "obs_id": r["obs_id"],
                "source_tool": r["source_tool"],
                "artifact_type": r["artifact_type"],
                "summary": r["summary"],
                "timestamp_unix_ms": r["timestamp_unix_ms"],
                "timestamp_label": r["timestamp_label"],
                "entities": json.loads(r["entities_json"] or "[]"),
                "provenance_path": r["provenance_path"],
                "confidence": r["confidence"],
                "flags": json.loads(r["flags_json"] or "[]"),
            })
        return out

    def list_entities(self, *, limit: int = 500) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM entities ORDER BY obs_count DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def timeline(self, *, limit: int = 5000) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT obs_id, source_tool, artifact_type, summary, "
            "timestamp_unix_ms, timestamp_label, entities_json, confidence "
            "FROM observations WHERE timestamp_unix_ms IS NOT NULL "
            "ORDER BY timestamp_unix_ms LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "obs_id": r["obs_id"],
                "when_ms": r["timestamp_unix_ms"],
                "when_label": r["timestamp_label"],
                "type": r["artifact_type"],
                "summary": r["summary"],
                "tool": r["source_tool"],
                "entities": json.loads(r["entities_json"] or "[]"),
                "confidence": r["confidence"],
            })
        return out
