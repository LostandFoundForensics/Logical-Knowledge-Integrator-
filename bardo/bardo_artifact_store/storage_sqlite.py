from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..bardo_core.schema import (
    Artifact, Entity, Event, Relationship,
    ArtifactType, EntityType, EventType, RelationshipType,
    Provenance, TimeAssertion, TimeRange, TimeSource,
    EntityRef, ArtifactRef,
)

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS entities (
    entity_id    TEXT PRIMARY KEY,
    entity_type  TEXT NOT NULL,
    labels_json  TEXT NOT NULL DEFAULT '[]',
    attrs_json   TEXT NOT NULL DEFAULT '{}',
    first_seen   TEXT,
    last_seen    TEXT,
    confidence   REAL NOT NULL DEFAULT 1.0,
    created_utc  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id   TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    subtype       TEXT NOT NULL DEFAULT '',
    summary       TEXT NOT NULL,
    payload_json  TEXT NOT NULL DEFAULT '{}',
    entities_json TEXT NOT NULL DEFAULT '[]',
    times_json    TEXT NOT NULL DEFAULT '[]',
    provenance_json TEXT NOT NULL,
    confidence    REAL NOT NULL DEFAULT 1.0,
    best_time     TEXT,
    created_utc   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_type     ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_time     ON artifacts(best_time);
CREATE INDEX IF NOT EXISTS idx_artifacts_conf     ON artifacts(confidence);

CREATE TABLE IF NOT EXISTS events (
    event_id      TEXT PRIMARY KEY,
    event_type    TEXT NOT NULL,
    description   TEXT NOT NULL,
    entities_json TEXT NOT NULL DEFAULT '[]',
    artifacts_json TEXT NOT NULL DEFAULT '[]',
    time_start    TEXT NOT NULL,
    time_end      TEXT NOT NULL,
    time_conf     REAL NOT NULL DEFAULT 1.0,
    location_json TEXT,
    confidence    REAL NOT NULL DEFAULT 1.0,
    created_utc   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type  ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(time_start);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id   TEXT PRIMARY KEY,
    from_entity_id    TEXT NOT NULL,
    to_entity_id      TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    artifacts_json    TEXT NOT NULL DEFAULT '[]',
    confidence        REAL NOT NULL DEFAULT 1.0,
    time_start        TEXT,
    time_end          TEXT,
    notes             TEXT NOT NULL DEFAULT '',
    created_utc       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_to   ON relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type);
"""


class BardoStore:
    """
    SQLite-backed artifact store for Bardo.
    Single abstraction layer — swap for Postgres by implementing the same interface.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    # ── Entities ──────────────────────────────────────────────────────────────

    def upsert_entity(self, entity: Entity) -> str:
        existing = self._conn.execute(
            "SELECT entity_id FROM entities WHERE entity_id=?", (entity.entity_id,)
        ).fetchone()

        if existing:
            self._conn.execute(
                "UPDATE entities SET labels_json=?, attrs_json=?, confidence=? WHERE entity_id=?",
                (json.dumps(entity.labels), json.dumps(entity.attributes),
                 entity.confidence, entity.entity_id),
            )
        else:
            self._conn.execute(
                "INSERT INTO entities(entity_id,entity_type,labels_json,attrs_json,"
                "first_seen,last_seen,confidence,created_utc) VALUES(?,?,?,?,?,?,?,?)",
                (
                    entity.entity_id,
                    entity.entity_type.value,
                    json.dumps(entity.labels),
                    json.dumps(entity.attributes),
                    entity.first_seen.to_dict() if entity.first_seen else None,
                    entity.last_seen.to_dict() if entity.last_seen else None,
                    entity.confidence,
                    _now(),
                ),
            )
        self._conn.commit()
        return entity.entity_id

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        row = self._conn.execute(
            "SELECT * FROM entities WHERE entity_id=?", (entity_id,)
        ).fetchone()
        if not row:
            return None
        return _row_to_entity(row)

    def find_entities_by_label(self, label: str) -> List[Entity]:
        rows = self._conn.execute(
            "SELECT * FROM entities WHERE labels_json LIKE ?",
            (f'%"{label}"%',),
        ).fetchall()
        return [_row_to_entity(r) for r in rows]

    def find_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        rows = self._conn.execute(
            "SELECT * FROM entities WHERE entity_type=?", (entity_type.value,)
        ).fetchall()
        return [_row_to_entity(r) for r in rows]

    # ── Artifacts ─────────────────────────────────────────────────────────────

    def insert_artifact(self, artifact: Artifact) -> str:
        best = artifact.best_time
        self._conn.execute(
            "INSERT OR REPLACE INTO artifacts("
            "artifact_id,artifact_type,subtype,summary,payload_json,"
            "entities_json,times_json,provenance_json,confidence,best_time,created_utc"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                artifact.artifact_id,
                artifact.artifact_type.value,
                artifact.subtype,
                artifact.summary,
                json.dumps(artifact.payload),
                json.dumps([e.to_dict() for e in artifact.related_entities]),
                json.dumps([t.to_dict() for t in artifact.observed_times]),
                json.dumps(artifact.source_provenance.to_dict()),
                artifact.confidence,
                best.isoformat() if best else None,
                _now(),
            ),
        )
        self._conn.commit()
        return artifact.artifact_id

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)
        ).fetchone()
        return dict(row) if row else None

    def query_artifacts_by_type(
        self, artifact_type: ArtifactType, limit: int = 500
    ) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE artifact_type=? ORDER BY best_time LIMIT ?",
            (artifact_type.value, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_artifacts_in_time_range(
        self, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE best_time >= ? AND best_time <= ? ORDER BY best_time",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_artifacts_by_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE entities_json LIKE ?",
            (f'%"{entity_id}"%',),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Events ────────────────────────────────────────────────────────────────

    def insert_event(self, event: Event) -> str:
        self._conn.execute(
            "INSERT OR REPLACE INTO events("
            "event_id,event_type,description,entities_json,artifacts_json,"
            "time_start,time_end,time_conf,location_json,confidence,created_utc"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.event_type.value,
                event.description,
                json.dumps([e.to_dict() for e in event.involved_entities]),
                json.dumps([a.to_dict() for a in event.supporting_artifacts]),
                event.time_window.earliest.isoformat(),
                event.time_window.latest.isoformat(),
                event.time_window.confidence,
                json.dumps(event.location.to_dict()) if event.location else None,
                event.confidence,
                _now(),
            ),
        )
        self._conn.commit()
        return event.event_id

    def query_events_in_range(
        self, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE time_start >= ? AND time_end <= ? ORDER BY time_start",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Relationships ─────────────────────────────────────────────────────────

    def insert_relationship(self, rel: Relationship) -> str:
        self._conn.execute(
            "INSERT OR REPLACE INTO relationships("
            "relationship_id,from_entity_id,to_entity_id,relationship_type,"
            "artifacts_json,confidence,time_start,time_end,notes,created_utc"
            ") VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                rel.relationship_id,
                rel.from_entity.entity_id,
                rel.to_entity.entity_id,
                rel.relationship_type.value,
                json.dumps([a.to_dict() for a in rel.supporting_artifacts]),
                rel.confidence,
                rel.time_window.earliest.isoformat() if rel.time_window else None,
                rel.time_window.latest.isoformat() if rel.time_window else None,
                rel.notes,
                _now(),
            ),
        )
        self._conn.commit()
        return rel.relationship_id

    def get_relationships_for_entity(
        self, entity_id: str
    ) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM relationships WHERE from_entity_id=? OR to_entity_id=?",
            (entity_id, entity_id),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        counts = {}
        for table in ("entities", "artifacts", "events", "relationships"):
            counts[table] = self._conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        return counts

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _row_to_entity(row: sqlite3.Row) -> Entity:
    return Entity(
        entity_id=row["entity_id"],
        entity_type=EntityType(row["entity_type"]),
        labels=json.loads(row["labels_json"]),
        attributes=json.loads(row["attrs_json"]),
        confidence=row["confidence"],
    )
