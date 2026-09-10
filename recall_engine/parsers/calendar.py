"""Calendar.sqlitedb via Manifest — read-only."""
from __future__ import annotations

from typing import List

from recall_engine.core.manifest import ManifestIndex
from recall_engine.core.models import ArtifactHit
from recall_engine.core.sqlite_ro import open_evidence_ro
from recall_engine.core.timeutil import apple_to_unix_ms
from recall_engine.parsers.base import Parser, ParserInfo


class CalendarParser(Parser):
    info = ParserInfo(
        parser_id="calendar",
        label="Calendar events",
        description="Event titles from Calendar.sqlitedb.",
    )

    def parse(self, manifest: ManifestIndex, *, limit: int = 20_000) -> List[ArtifactHit]:
        entries = manifest.find(contains="Calendar", limit=30)
        entries += manifest.find(endswith="Calendar.sqlitedb", limit=10)
        hits: List[ArtifactHit] = []
        seen = set()
        for e in entries:
            if e.file_id in seen:
                continue
            if "sqlitedb" not in e.relative_path.lower() and "Calendar.sqlitedb" not in e.relative_path:
                if not e.relative_path.endswith(".sqlitedb"):
                    continue
            seen.add(e.file_id)
            real = manifest.resolve(e.file_id)
            if not real:
                continue
            try:
                hits.extend(self._parse_db(real, e, limit=limit - len(hits)))
            except Exception:
                continue
            if len(hits) >= limit:
                break
        return hits[:limit]

    def _parse_db(self, db, entry, *, limit: int) -> List[ArtifactHit]:
        out: List[ArtifactHit] = []
        conn = open_evidence_ro(db)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            table = "CalendarItem" if "CalendarItem" in tables else (
                "ZCALENDARITEM" if "ZCALENDARITEM" in tables else None
            )
            if not table:
                return out
            cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
            title_col = next(
                (c for c in ("summary", "ZTITLE", "title", "ZSUMMARY") if c in cols),
                None,
            )
            start_col = next(
                (c for c in ("start_date", "ZSTARTDATE", "startDate") if c in cols),
                None,
            )
            if not title_col:
                return out
            select = [f'"{title_col}"']
            if start_col:
                select.append(f'"{start_col}"')
            sql = f'SELECT {", ".join(select)} FROM "{table}" WHERE "{title_col}" IS NOT NULL LIMIT ?'
            for row in conn.execute(sql, (limit,)):
                title = row[title_col]
                raw_s = row[start_col] if start_col else None
                unix_ms = apple_to_unix_ms(raw_s, unit="seconds")
                out.append(
                    ArtifactHit(
                        artifact_type="ios.calendar_event",
                        summary=str(title)[:200],
                        record={
                            "title": title,
                            "start_raw": raw_s,
                            "start_unix_ms": unix_ms,
                        },
                        source_path=entry.relative_path,
                        domain=entry.domain,
                        file_id=entry.file_id,
                        confidence=0.85,
                    )
                )
        finally:
            conn.close()
        return out
