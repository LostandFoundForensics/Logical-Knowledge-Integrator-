"""
TimelineStore — SQLite workspace for ChronoChain.

This database is *created by us* under the case folder, so it is read-write.
Source evidence is never opened here.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from chronochain.core.schema import TimelineEvent, Timestamp, Provenance
from chronochain.core.normalize import epoch_ms_to_iso

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  epoch_ms INTEGER NOT NULL,
  ts_type TEXT NOT NULL,
  ts_confidence REAL NOT NULL,
  ts_original_value TEXT NOT NULL,
  ts_original_format TEXT NOT NULL,
  ts_timezone_hint TEXT,
  ts_notes TEXT,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  actors_json TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  attributes_json TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  source_path TEXT NOT NULL,
  extractor TEXT NOT NULL,
  recipe TEXT NOT NULL,
  artifact_ref TEXT NOT NULL,
  hash_chain_json TEXT NOT NULL,
  observed INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_time ON events(epoch_ms);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_source_path ON events(source_path);
CREATE INDEX IF NOT EXISTS idx_events_evidence_id ON events(evidence_id);
CREATE INDEX IF NOT EXISTS idx_events_extractor ON events(extractor);
CREATE INDEX IF NOT EXISTS idx_events_observed ON events(observed);

CREATE TABLE IF NOT EXISTS links (
  link_id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_event_id TEXT NOT NULL,
  to_event_id TEXT NOT NULL,
  link_type TEXT NOT NULL,
  strength REAL NOT NULL,
  inferred INTEGER NOT NULL,
  rationale TEXT NOT NULL,
  evidence_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_event_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_event_id);
"""


def safe_iso(epoch_ms: Any) -> str:
    try:
        v = int(epoch_ms)
        return epoch_ms_to_iso(v) if v > 0 else "—"
    except Exception:
        return "—"


class TimelineStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.executescript(SCHEMA_SQL)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def __enter__(self) -> "TimelineStore":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _ev_to_row(self, ev: TimelineEvent) -> tuple:
        return (
            ev.event_id,
            int(ev.ts.epoch_ms),
            ev.ts.ts_type,
            float(ev.ts.confidence),
            ev.ts.original_value,
            ev.ts.original_format,
            ev.ts.timezone_hint,
            ev.ts.notes,
            ev.category,
            ev.title,
            ev.description,
            json.dumps(ev.actors, ensure_ascii=False),
            json.dumps(ev.tags, ensure_ascii=False),
            json.dumps(ev.attributes, ensure_ascii=False),
            ev.provenance.evidence_id,
            ev.provenance.source_path,
            ev.provenance.extractor,
            ev.provenance.recipe,
            ev.provenance.artifact_ref,
            json.dumps(ev.provenance.hash_chain, ensure_ascii=False),
            1 if ev.observed else 0,
        )

    def upsert_event(self, ev: TimelineEvent) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO events (
                    event_id, epoch_ms, ts_type, ts_confidence,
                    ts_original_value, ts_original_format, ts_timezone_hint, ts_notes,
                    category, title, description,
                    actors_json, tags_json, attributes_json,
                    evidence_id, source_path, extractor, recipe, artifact_ref,
                    hash_chain_json, observed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._ev_to_row(ev),
            )

    def upsert_many(self, events: Iterable[TimelineEvent]) -> int:
        n = 0
        with self.conn:
            for ev in events:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO events (
                        event_id, epoch_ms, ts_type, ts_confidence,
                        ts_original_value, ts_original_format, ts_timezone_hint, ts_notes,
                        category, title, description,
                        actors_json, tags_json, attributes_json,
                        evidence_id, source_path, extractor, recipe, artifact_ref,
                        hash_chain_json, observed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._ev_to_row(ev),
                )
                n += 1
        return n

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
        return int(row["c"]) if row else 0

    def list_events(
        self,
        *,
        limit: int = 10_000,
        category: Optional[str] = None,
        after_ms: Optional[int] = None,
        before_ms: Optional[int] = None,
    ) -> List[TimelineEvent]:
        clauses = ["1=1"]
        params: List[Any] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if after_ms is not None:
            clauses.append("epoch_ms >= ?")
            params.append(after_ms)
        if before_ms is not None:
            clauses.append("epoch_ms <= ?")
            params.append(before_ms)
        params.append(limit)
        sql = f"""
            SELECT * FROM events
            WHERE {' AND '.join(clauses)}
            ORDER BY epoch_ms ASC, event_id ASC
            LIMIT ?
        """
        out: List[TimelineEvent] = []
        for row in self.conn.execute(sql, params):
            out.append(self._row_to_ev(row))
        return out

    def _row_to_ev(self, row: sqlite3.Row) -> TimelineEvent:
        return TimelineEvent(
            event_id=row["event_id"],
            ts=Timestamp(
                epoch_ms=int(row["epoch_ms"]),
                ts_type=row["ts_type"],
                confidence=float(row["ts_confidence"]),
                original_value=row["ts_original_value"] or "",
                original_format=row["ts_original_format"] or "",
                timezone_hint=row["ts_timezone_hint"] or "UTC",
                notes=row["ts_notes"] or "",
            ),
            category=row["category"],
            title=row["title"],
            description=row["description"] or "",
            actors=json.loads(row["actors_json"] or "[]"),
            tags=json.loads(row["tags_json"] or "[]"),
            attributes=json.loads(row["attributes_json"] or "{}"),
            provenance=Provenance(
                evidence_id=row["evidence_id"] or "",
                source_path=row["source_path"] or "",
                extractor=row["extractor"] or "",
                recipe=row["recipe"] or "",
                artifact_ref=row["artifact_ref"] or "",
                hash_chain=json.loads(row["hash_chain_json"] or "[]"),
            ),
            observed=bool(row["observed"]),
        )

    def save_links(self, links: List[Dict[str, Any]]) -> int:
        with self.conn:
            self.conn.execute("DELETE FROM links")
            for link in links:
                self.conn.execute(
                    """
                    INSERT INTO links (
                        from_event_id, to_event_id, link_type, strength,
                        inferred, rationale, evidence_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        link["from_event_id"],
                        link["to_event_id"],
                        link["link_type"],
                        float(link.get("strength", 0.5)),
                        1 if link.get("inferred") else 0,
                        link.get("rationale", ""),
                        link.get("evidence_json", "{}"),
                    ),
                )
        return len(links)
