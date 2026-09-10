"""
Sundial — Demo Bundle Generator
Creates a complete, schema-valid case bundle so Sundial can be run and tested
without waiting for an upstream LoKi tool. Also used by the self-test.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sundial.core.bundle import init_empty_db
from sundial.core.schema import SCHEMA_VERSION


def build_demo_bundle(bundle_dir: str) -> str:
    root = Path(bundle_dir)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "ledger").mkdir(parents=True, exist_ok=True)

    case_id = str(uuid.uuid4())
    case = {
        "case_id": case_id,
        "case_name": "Demo — Riverside Inquiry",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "owner_label": "J. Okafor",
        "device_label": "iPhone 14",
        "notes": "Synthetic demo bundle for Sundial.",
        "schema_version": SCHEMA_VERSION,
    }
    (root / "case.json").write_text(json.dumps(case, indent=2), encoding="utf-8")

    db_path = root / "loki_normalized.db"
    if db_path.exists():
        db_path.unlink()
    init_empty_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    base = datetime(2025, 3, 8, 9, 0, 0, tzinfo=timezone.utc)

    def iso(mins: int) -> str:
        return (base + timedelta(minutes=mins)).isoformat()

    events = [
        ("COMMS", 0,  "EXACT", "DEVICE", "Message sent to +1 555 0100",
         "sms.db message ROWID=1481 is_from_me=1", 0.95, 1),
        ("COMMS", 1,  "EXACT", "DEVICE", "Reply received from +1 555 0100",
         "sms.db message ROWID=1482 is_from_me=0", 0.95, 1),
        ("MEDIA", 150, "EXACT", "UTC", "Photo captured (GPS present)",
         "Photos.sqlite ZASSET ZDATECREATED", 0.90, 1),
        ("COMMS", 302, "EXACT", "DEVICE", "Outgoing call, 4m 12s",
         "CallHistory.storedata ZCALLRECORD Z_PK=22", 0.93, 1),
        ("WEB",  595, "EXACT", "UTC", "Safari visit: weather.example",
         "History.db urls id=88", 0.88, 1),
    ]
    for i, (cat, m, q, tz, plain, tech, conf, sc) in enumerate(events, 1):
        eid = f"ev-{i:04d}"
        conn.execute(
            """INSERT INTO events
               (event_id, category, timestamp_start, timestamp_end, timestamp_quality,
                timezone_basis, summary_plain, summary_technical, observability,
                confidence, source_count, thread_key)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, cat, iso(m), None, q, tz, plain, tech, "OBSERVED", conf, sc,
             "thread-100" if cat == "COMMS" else None),
        )
        conn.execute(
            """INSERT INTO event_sources
               (event_id, source_path, source_type, table_name, record_id,
                parser_name, parser_version)
               VALUES (?,?,?,?,?,?,?)""",
            (eid, f"/evidence/{cat.lower()}.db", "db", cat.lower(),
             str(1000 + i), "iDriller", "1.0"),
        )

    # A conflict: two parsers disagree on the call timestamp
    conn.execute(
        """INSERT INTO event_conflicts
           (conflict_id, event_id, conflict_type, field_name, a_value, b_value,
            a_source_id, b_source_id, severity, note_plain)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        ("cf-1", "ev-0004", "TIMESTAMP", "timestamp_start",
         iso(302), iso(303), 4, 4, "LOW",
         "Two parsers read the call time one minute apart."),
    )

    # An inferred event in its OWN table
    conn.execute(
        """INSERT INTO inferred_events
           (event_id, inference_type, timestamp_estimated, timestamp_range_start,
            timestamp_range_end, summary_plain, confidence, confidence_level,
            confidence_reasons, supporting_event_ids, hidden)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ("inf-0001", "LIKELY_APP_INTERACTION", iso(120), iso(118), iso(123),
         "Likely interacted with Telegram", 0.78, "MEDIUM",
         json.dumps(["App was in foreground",
                     "Notification interaction within 3 minutes",
                     "Same thread key"]),
         json.dumps(["ev-0002", "ev-0003"]), 0),
    )

    # A gap
    conn.execute(
        """INSERT INTO timeline_gaps
           (gap_id, gap_start, gap_end, duration_minutes, gap_explained, explanations)
           VALUES (?,?,?,?,?,?)""",
        ("gap-1", iso(303), iso(595), 292, 0, json.dumps([])),
    )

    conn.commit()
    conn.close()

    (root / "ledger" / "hashes.manifest.txt").write_text(
        "SHA256  (demo)  loki_normalized.db\n", encoding="utf-8")
    (root / "logs" / "acquisition.log").write_text("demo acquisition log\n", encoding="utf-8")

    return str(root)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "cases/DemoCase"
    print(build_demo_bundle(out))
