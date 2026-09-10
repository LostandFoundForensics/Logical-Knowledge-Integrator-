"""Apple Notes (NoteStore.sqlite) via Manifest — read-only."""
from __future__ import annotations

from typing import List

from recall_engine.core.manifest import ManifestIndex
from recall_engine.core.models import ArtifactHit
from recall_engine.core.sqlite_ro import open_evidence_ro
from recall_engine.core.timeutil import apple_to_unix_ms
from recall_engine.parsers.base import Parser, ParserInfo


class NotesParser(Parser):
    info = ParserInfo(
        parser_id="notes",
        label="Apple Notes",
        description="Note titles from NoteStore.sqlite in the backup.",
    )

    def parse(self, manifest: ManifestIndex, *, limit: int = 20_000) -> List[ArtifactHit]:
        entries = manifest.find(contains="NoteStore", limit=20)
        entries += manifest.find(endswith="NoteStore.sqlite", limit=10)
        hits: List[ArtifactHit] = []
        seen = set()
        for e in entries:
            if e.file_id in seen:
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
            # Modern NoteStore uses ZICCLOUDSYNCINGOBJECT
            table = None
            for cand in ("ZICCLOUDSYNCINGOBJECT", "ZNOTE", "Note"):
                if cand in tables:
                    table = cand
                    break
            if not table:
                return out
            cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
            title_col = next(
                (c for c in ("ZTITLE", "ZTITLE1", "title", "Title") if c in cols),
                None,
            )
            date_col = next(
                (c for c in ("ZMODIFICATIONDATE1", "ZCREATIONDATE", "ZMODIFICATIONDATE") if c in cols),
                None,
            )
            if not title_col:
                return out
            select = [f'"{title_col}"']
            if date_col:
                select.append(f'"{date_col}"')
            sql = f'SELECT {", ".join(select)} FROM "{table}" WHERE "{title_col}" IS NOT NULL LIMIT ?'
            for row in conn.execute(sql, (limit,)):
                title = row[title_col]
                if not title:
                    continue
                raw_d = row[date_col] if date_col else None
                unix_ms = apple_to_unix_ms(raw_d, unit="seconds")
                out.append(
                    ArtifactHit(
                        artifact_type="ios.note",
                        summary=str(title)[:200],
                        record={
                            "title": title,
                            "date_raw": raw_d,
                            "date_unix_ms": unix_ms,
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
