import sqlite3
from typing import List
from .models import GapFinding


def analyze_gaps(loki_db_path: str) -> List[GapFinding]:
    gaps: List[GapFinding] = []
    cx = sqlite3.connect(loki_db_path)
    cur = cx.cursor()

    cur.execute("SELECT source_provider FROM artifact_message GROUP BY source_provider HAVING COUNT(*) > 0")
    providers_with_messages = {r[0] for r in cur.fetchall()}

    cur.execute("SELECT DISTINCT source_provider FROM artifact_event")
    providers_with_events = {r[0] for r in cur.fetchall()}

    for p in providers_with_messages:
        if p not in providers_with_events:
            gaps.append(GapFinding(
                category="absence",
                description="Messages present but no calendar/events present for provider",
                affected_providers=[p],
                evidence={},
            ))

    cur.execute("""
        SELECT COUNT(*) FROM artifact_message
        WHERE date_raw IS NOT NULL AND timestamp_parsed_utc IS NULL
    """)
    partial = cur.fetchone()[0]
    if partial > 0:
        gaps.append(GapFinding(
            category="partial",
            description="Messages with timestamps lacking timezone / UTC normalization",
            affected_providers=["multiple"],
            evidence={"count": partial},
        ))

    cx.close()
    return gaps
