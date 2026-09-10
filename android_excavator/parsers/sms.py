"""SMS / MMS from Android telephony databases (read-only)."""
from __future__ import annotations

from pathlib import Path
from typing import List

from android_excavator.core.models import ArtifactRecord, Provenance, Quality
from android_excavator.core.source import FolderDump
from android_excavator.core.sqlite_ro import open_evidence_ro
from android_excavator.parsers.base import Parser, ParserInfo


class SmsParser(Parser):
    info = ParserInfo(
        parser_id="sms",
        label="Text messages (SMS)",
        description="Reads SMS from mmssms.db or similar telephony databases.",
        category="communications",
    )

    CANDIDATE_NAMES = ("mmssms.db", "sms.db", "telephony.db")

    def parse(self, dump: FolderDump, *, limit: int = 50_000) -> List[ArtifactRecord]:
        records: List[ArtifactRecord] = []
        paths: List[Path] = []
        for name in self.CANDIDATE_NAMES:
            paths.extend(dump.find_by_name(name))
        # Also common under providers path
        paths.extend(dump.find_path_contains("com.android.providers.telephony"))
        paths = list({p.resolve() for p in paths if p.suffix.lower() in (".db", "")})

        for db_path in paths:
            if not db_path.is_file() or db_path.suffix.lower() != ".db":
                continue
            try:
                records.extend(self._parse_db(dump, db_path, limit=limit - len(records)))
            except Exception:
                continue
            if len(records) >= limit:
                break
        return records[:limit]

    def _parse_db(self, dump: FolderDump, db_path: Path, *, limit: int) -> List[ArtifactRecord]:
        out: List[ArtifactRecord] = []
        logical = dump.logical_path(db_path)
        try:
            digest = dump.sha256_file(db_path)
        except Exception:
            digest = ""

        conn = open_evidence_ro(db_path)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            table = next((t for t in ("sms", "messages", "message") if t in tables), None)
            if not table:
                return out
            cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
            date_col = next((c for c in ("date", "date_sent", "time") if c in cols), None)
            body_col = next((c for c in ("body", "text") if c in cols), None)
            addr_col = next((c for c in ("address", "sender", "number") if c in cols), None)
            type_col = "type" if "type" in cols else None
            if not date_col:
                return out

            select = ["ROWID", f'"{date_col}"']
            if body_col:
                select.append(f'"{body_col}"')
            if addr_col:
                select.append(f'"{addr_col}"')
            if type_col:
                select.append(f'"{type_col}"')
            sql = f'SELECT {", ".join(select)} FROM "{table}" ORDER BY "{date_col}" LIMIT ?'
            for row in conn.execute(sql, (limit,)):
                rec = {
                    "rowid": row["ROWID"],
                    "date": row[date_col],
                    "body": row[body_col] if body_col else None,
                    "address": row[addr_col] if addr_col else None,
                    "type": row[type_col] if type_col else None,
                    "table": table,
                }
                out.append(
                    ArtifactRecord(
                        artifact_type="android.sms",
                        record=rec,
                        provenance=Provenance(
                            source_logical_path=logical,
                            source_real_path=str(db_path),
                            source_sha256=digest,
                        ),
                        quality=Quality(confidence=0.9),
                    )
                )
        finally:
            conn.close()
        return out
