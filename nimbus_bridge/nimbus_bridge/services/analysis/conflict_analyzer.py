"""
nimbus_bridge/services/analysis/conflict_analyzer.py

NOTE: the body_text equality join will produce false positives for
short or common messages (e.g. two unrelated "ok" replies). These
are flagged as conditions, not conclusions — callers should treat
all conflict findings as candidates requiring human review, not as
confirmed duplicates.
"""
import sqlite3
from typing import List
from .models import ConflictFinding


def analyze_conflicts(loki_db_path: str) -> List[ConflictFinding]:
    conflicts: List[ConflictFinding] = []
    cx = sqlite3.connect(loki_db_path)
    cur = cx.cursor()

    cur.execute("""
        SELECT m1.artifact_id, m2.artifact_id, m1.body_text, m1.date_raw, m2.date_raw
        FROM artifact_message m1
        JOIN artifact_message m2
          ON m1.body_text = m2.body_text
         AND m1.artifact_id != m2.artifact_id
        WHERE m1.date_raw != m2.date_raw
          AND m1.body_text IS NOT NULL
          AND length(m1.body_text) > 20
    """)
    for a1, a2, body, t1, t2 in cur.fetchall():
        conflicts.append(ConflictFinding(
            category="timestamp",
            description="Identical message content with differing raw timestamps",
            left_artifact_id=a1,
            right_artifact_id=a2,
            evidence={"date_left": t1, "date_right": t2},
        ))

    cx.close()
    return conflicts
