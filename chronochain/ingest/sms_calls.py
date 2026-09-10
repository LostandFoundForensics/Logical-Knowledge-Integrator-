"""
SMS / call log ingest.

Opens source SQLite evidence **read-only**.
Supports common Android mmssms.db and a generic messages table shape.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import List, Optional

from chronochain.core.schema import TimelineEvent, Timestamp, Provenance
from chronochain.core.normalize import parse_to_epoch_ms


def _open_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only = ON")
    except Exception:
        pass
    conn.execute("SELECT 1")
    return conn


def _eid(*parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return h[:24]


def ingest_android_sms(
    db_path: Path,
    *,
    evidence_id: str = "",
    limit: int = 50_000,
) -> List[TimelineEvent]:
    """Read Android Telephony/mmssms-style SMS into timeline events."""
    events: List[TimelineEvent] = []
    path = Path(db_path)
    if not path.is_file():
        return events

    conn = _open_ro(path)
    try:
        # Discover a usable table
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        table = None
        for candidate in ("sms", "messages", "message"):
            if candidate in tables:
                table = candidate
                break
        if not table:
            return events

        cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
        # date column variants
        date_col = next((c for c in ("date", "date_sent", "time", "timestamp") if c in cols), None)
        body_col = next((c for c in ("body", "text", "message") if c in cols), None)
        addr_col = next((c for c in ("address", "sender", "number") if c in cols), None)
        if not date_col:
            return events

        select_cols = [date_col]
        if body_col:
            select_cols.append(body_col)
        if addr_col:
            select_cols.append(addr_col)
        if "type" in cols:
            select_cols.append("type")
        if "ROWID" in cols or True:
            pass

        col_sql = ", ".join(f'"{c}"' for c in select_cols)
        sql = f'SELECT ROWID, {col_sql} FROM "{table}" ORDER BY "{date_col}" LIMIT ?'
        for row in conn.execute(sql, (limit,)):
            raw_date = row[date_col]
            # Android SMS date is usually unix ms
            epoch = parse_to_epoch_ms(raw_date, encoding="unix_ms")
            if epoch is None:
                epoch = parse_to_epoch_ms(raw_date, encoding="unix_s")
            if epoch is None:
                continue
            addr = str(row[addr_col]) if addr_col and row[addr_col] is not None else ""
            body = str(row[body_col]) if body_col and row[body_col] is not None else ""
            title = f"SMS {'with ' + addr if addr else ''}".strip()
            events.append(
                TimelineEvent(
                    event_id=_eid("sms", str(row["ROWID"]), str(epoch)),
                    ts=Timestamp(
                        epoch_ms=epoch,
                        ts_type="EXACT",
                        confidence=0.9,
                        original_value=str(raw_date),
                        original_format="unix_ms",
                    ),
                    category="COMMS",
                    title=title or "SMS",
                    description=(body[:200] + ("…" if len(body) > 200 else "")),
                    actors=[addr] if addr else [],
                    tags=["sms"],
                    attributes={"rowid": row["ROWID"]},
                    provenance=Provenance(
                        evidence_id=evidence_id or path.name,
                        source_path=str(path),
                        extractor="chronochain.ingest.sms_calls",
                        recipe="android_sms",
                        artifact_ref=f"{table}/ROWID={row['ROWID']}",
                    ),
                )
            )
    finally:
        conn.close()
    return events


def ingest_generic_messages_json(
    records: List[dict],
    *,
    evidence_id: str = "",
    source_path: str = "",
) -> List[TimelineEvent]:
    """Ingest already-parsed message dicts (e.g. from MyRecord export)."""
    events: List[TimelineEvent] = []
    for i, rec in enumerate(records):
        raw = rec.get("date") or rec.get("timestamp") or rec.get("ts")
        epoch = parse_to_epoch_ms(raw, encoding="unix_ms")
        if epoch is None:
            epoch = parse_to_epoch_ms(raw, encoding="unix_s")
        if epoch is None:
            epoch = parse_to_epoch_ms(raw, encoding="apple_absolute")
        if epoch is None:
            continue
        addr = str(rec.get("address") or rec.get("sender") or "")
        body = str(rec.get("text") or rec.get("body") or "")
        events.append(
            TimelineEvent(
                event_id=_eid("msg", str(rec.get("id", i)), str(epoch)),
                ts=Timestamp(
                    epoch_ms=epoch,
                    ts_type="EXACT",
                    confidence=0.85,
                    original_value=str(raw),
                    original_format="unknown",
                ),
                category="COMMS",
                title=f"Message {'with ' + addr if addr else ''}".strip() or "Message",
                description=body[:200],
                actors=[addr] if addr else [],
                tags=["message"],
                attributes=dict(rec),
                provenance=Provenance(
                    evidence_id=evidence_id,
                    source_path=source_path,
                    extractor="chronochain.ingest.sms_calls",
                    recipe="generic_json",
                ),
            )
        )
    return events
