from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...bardo_core.schema import (
    Artifact, Entity, Relationship,
    ArtifactType, EntityType, RelationshipType,
    Provenance, TimeAssertion, TimeRange, TimeSource,
    EntityRef,
)
from ...bardo_artifact_store.storage_sqlite import BardoStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prov(tool: str, source_file: str, source_hash: str = "") -> Provenance:
    return Provenance(
        acquisition_tool=tool,
        tool_version="loki-adapter-1.0",
        source_file=source_file,
        source_hash=source_hash,
        ingest_time=_now(),
        transformation_steps=["loki_bardo_adapter"],
    )


class IDriverAdapter:
    """Ingests iDriller evidence SQLite output into Bardo."""

    tool_name = "idriller"

    def ingest(self, evidence_db_path: Path, store: BardoStore) -> Dict[str, int]:
        import sqlite3
        counts = {"messages": 0, "calls": 0, "web": 0, "people": 0}

        if not evidence_db_path.exists():
            return counts

        # Treat incoming evidence DB as source evidence — read-only
        uri = f"file:{Path(evidence_db_path).resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA query_only = ON")
        except Exception:
            pass
        prov = _prov(self.tool_name, str(evidence_db_path))

        # ── Messages ─────────────────────────────────────────────────────────
        try:
            for row in conn.execute("SELECT * FROM messages ORDER BY ts_utc"):
                rec = dict(row)
                ts = _parse_iso(rec.get("ts_utc"))
                times = []
                if ts:
                    times.append(TimeAssertion(
                        source=TimeSource.APP_LOG,
                        confidence=0.90 if rec.get("confidence") == "high" else 0.70,
                        timestamp=ts,
                    ))

                # Entity: sender / recipient
                entities = []
                for field in ("sender_identifier", "recipient_identifier", "thread_key"):
                    val = rec.get(field)
                    if val:
                        entity = Entity(
                            entity_type=EntityType.PERSON,
                            labels=[val],
                            attributes={"identifier": val, "source": "idriller_messages"},
                        )
                        store.upsert_entity(entity)
                        entities.append(entity.to_ref())

                artifact = Artifact(
                    artifact_type=ArtifactType.MESSAGE,
                    subtype=rec.get("service", "sms"),
                    summary=(rec.get("body") or "")[:120] or "Message (no body)",
                    payload=rec,
                    source_provenance=prov,
                    related_entities=entities,
                    observed_times=times,
                    confidence=0.90 if rec.get("confidence") == "high" else 0.70,
                )
                store.insert_artifact(artifact)
                counts["messages"] += 1
        except Exception:
            pass

        # ── Calls ─────────────────────────────────────────────────────────────
        try:
            for row in conn.execute("SELECT * FROM calls ORDER BY ts_utc"):
                rec = dict(row)
                ts = _parse_iso(rec.get("ts_utc"))
                times = []
                if ts:
                    times.append(TimeAssertion(
                        source=TimeSource.APP_LOG,
                        confidence=0.88,
                        timestamp=ts,
                    ))

                entity = None
                if rec.get("remote_identifier"):
                    entity = Entity(
                        entity_type=EntityType.PERSON,
                        labels=[rec["remote_identifier"]],
                        attributes={"phone": rec["remote_identifier"]},
                    )
                    store.upsert_entity(entity)

                artifact = Artifact(
                    artifact_type=ArtifactType.CALL,
                    subtype=rec.get("direction", "unknown"),
                    summary=f"{rec.get('direction','?')} call with {rec.get('remote_identifier','unknown')}",
                    payload=rec,
                    source_provenance=prov,
                    related_entities=[entity.to_ref()] if entity else [],
                    observed_times=times,
                    confidence=0.88,
                )
                store.insert_artifact(artifact)
                counts["calls"] += 1
        except Exception:
            pass

        # ── Web history ───────────────────────────────────────────────────────
        try:
            for row in conn.execute("SELECT * FROM web_history ORDER BY ts_utc"):
                rec = dict(row)
                ts = _parse_iso(rec.get("ts_utc"))
                times = []
                if ts:
                    times.append(TimeAssertion(
                        source=TimeSource.APP_LOG,
                        confidence=0.85,
                        timestamp=ts,
                    ))

                artifact = Artifact(
                    artifact_type=ArtifactType.WEB_ACTIVITY,
                    subtype="safari_history",
                    summary=(rec.get("title") or rec.get("url") or "Web visit")[:120],
                    payload=rec,
                    source_provenance=prov,
                    observed_times=times,
                    confidence=0.85,
                )
                store.insert_artifact(artifact)
                counts["web"] += 1
        except Exception:
            pass

        # ── People ─────────────────────────────────────────────────────────────
        try:
            for row in conn.execute("SELECT * FROM people"):
                rec = dict(row)
                entity = Entity(
                    entity_type=EntityType.PERSON,
                    labels=[rec.get("identifier", "unknown")],
                    attributes={
                        "identifier": rec.get("identifier"),
                        "label": rec.get("label"),
                        "source": "idriller_contacts",
                    },
                )
                store.upsert_entity(entity)
                counts["people"] += 1
        except Exception:
            pass

        conn.close()
        return counts


class AndroidExcavatorAdapter:
    """Ingests Android Excavator case SQLite output into Bardo."""

    tool_name = "android_excavator"

    def ingest(self, case_db_path: Path, store: BardoStore) -> Dict[str, int]:
        import sqlite3
        counts = {"artifacts": 0, "events": 0}

        if not case_db_path.exists():
            return counts

        # Ingested case DB treated as evidence input — read-only
        uri = f"file:{Path(case_db_path).resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA query_only = ON")
        except Exception:
            pass
        prov = _prov(self.tool_name, str(case_db_path))

        try:
            for row in conn.execute("SELECT * FROM events ORDER BY timestamp_ms"):
                rec = dict(row)
                ts = _ms_to_datetime(rec.get("timestamp_ms"))
                times = []
                if ts:
                    times.append(TimeAssertion(
                        source=TimeSource.APP_LOG,
                        confidence=0.85,
                        timestamp=ts,
                    ))

                # Map event_type to ArtifactType
                atype = _map_android_event_type(rec.get("event_type", ""))

                entities_raw = rec.get("entities_json", "{}")
                try:
                    entities_dict = json.loads(entities_raw)
                except Exception:
                    entities_dict = {}

                entities = []
                for k, v in entities_dict.items():
                    if v:
                        entity = Entity(
                            entity_type=EntityType.PERSON,
                            labels=[str(v)],
                            attributes={k: v, "source": "android_excavator"},
                        )
                        store.upsert_entity(entity)
                        entities.append(entity.to_ref())

                artifact = Artifact(
                    artifact_type=atype,
                    subtype=rec.get("event_type", ""),
                    summary=rec.get("summary", "Android artifact")[:120],
                    payload=rec,
                    source_provenance=prov,
                    related_entities=entities,
                    observed_times=times,
                    confidence=0.85,
                )
                store.insert_artifact(artifact)
                counts["artifacts"] += 1
        except Exception:
            pass

        conn.close()
        return counts


class RecallEngineAdapter:
    """Ingests Recall Engine timeline JSON output into Bardo."""

    tool_name = "recall_engine"

    def ingest(self, timeline_json_path: Path, store: BardoStore) -> Dict[str, int]:
        counts = {"events": 0}

        if not timeline_json_path.exists():
            return counts

        with timeline_json_path.open(encoding="utf-8") as f:
            events = json.load(f)

        prov = _prov(self.tool_name, str(timeline_json_path))

        for event in events:
            ts = _parse_iso(event.get("ts"))
            times = []
            if ts:
                times.append(TimeAssertion(
                    source=TimeSource.APP_LOG,
                    confidence=0.85 if event.get("confidence") == "high" else 0.65,
                    timestamp=ts,
                ))

            atype = _map_recall_kind(event.get("kind", ""))

            artifact = Artifact(
                artifact_type=atype,
                subtype=event.get("kind", ""),
                summary=event.get("title") or event.get("description") or "Recall event",
                payload=event,
                source_provenance=prov,
                observed_times=times,
                confidence=0.85,
            )
            store.insert_artifact(artifact)
            counts["events"] += 1

        return counts


# ── Utilities ─────────────────────────────────────────────────────────────────

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

def _ms_to_datetime(ms: Optional[int]) -> Optional[datetime]:
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    except Exception:
        return None

def _map_android_event_type(event_type: str) -> ArtifactType:
    mapping = {
        "communication.sms":    ArtifactType.MESSAGE,
        "communication.call":   ArtifactType.CALL,
        "web.visit":            ArtifactType.WEB_ACTIVITY,
        "app.usage":            ArtifactType.APP_ACTIVITY,
        "app.install_state":    ArtifactType.INSTALL_EVENT,
        "media.present":        ArtifactType.MEDIA,
        "notification.received": ArtifactType.SYSTEM_EVENT,
    }
    return mapping.get(event_type, ArtifactType.UNKNOWN)

def _map_recall_kind(kind: str) -> ArtifactType:
    mapping = {
        "message":      ArtifactType.MESSAGE,
        "web":          ArtifactType.WEB_ACTIVITY,
        "app_activity": ArtifactType.APP_ACTIVITY,
    }
    return mapping.get(kind, ArtifactType.UNKNOWN)
