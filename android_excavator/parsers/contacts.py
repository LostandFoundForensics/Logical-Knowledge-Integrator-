"""Contacts from contacts2.db / people databases (read-only)."""
from __future__ import annotations

from pathlib import Path
from typing import List

from android_excavator.core.models import ArtifactRecord, Provenance, Quality
from android_excavator.core.source import FolderDump
from android_excavator.core.sqlite_ro import open_evidence_ro
from android_excavator.parsers.base import Parser, ParserInfo


class ContactsParser(Parser):
    info = ParserInfo(
        parser_id="contacts",
        label="Contacts (address book)",
        description="Reads names and phone numbers from the Android contacts database.",
        category="people",
    )

    def parse(self, dump: FolderDump, *, limit: int = 50_000) -> List[ArtifactRecord]:
        records: List[ArtifactRecord] = []
        paths = dump.find_by_name("contacts2.db")
        paths += dump.find_path_contains("com.android.providers.contacts")
        paths = list({p.resolve() for p in paths if p.suffix.lower() == ".db"})

        for db_path in paths:
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
            # Prefer data+raw_contacts join style; fall back to simple people table
            if "raw_contacts" in tables and "data" in tables:
                sql = """
                    SELECT rc._id AS contact_id,
                           rc.display_name AS display_name,
                           d.data1 AS value,
                           d.mimetype AS mimetype
                    FROM raw_contacts rc
                    LEFT JOIN data d ON d.raw_contact_id = rc._id
                    LIMIT ?
                """
                for row in conn.execute(sql, (limit * 3,)):
                    out.append(
                        ArtifactRecord(
                            artifact_type="android.contact",
                            record={
                                "contact_id": row["contact_id"],
                                "display_name": row["display_name"],
                                "value": row["value"],
                                "mimetype": row["mimetype"],
                            },
                            provenance=Provenance(
                                source_logical_path=logical,
                                source_real_path=str(db_path),
                                source_sha256=digest,
                            ),
                            quality=Quality(confidence=0.85, flags=["best_effort_join"]),
                        )
                    )
                    if len(out) >= limit:
                        break
            elif "contacts" in tables or "people" in tables:
                table = "contacts" if "contacts" in tables else "people"
                cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
                name_col = next(
                    (c for c in ("display_name", "name", "displayName") if c in cols),
                    None,
                )
                if name_col:
                    for row in conn.execute(
                        f'SELECT ROWID, "{name_col}" AS display_name FROM "{table}" LIMIT ?',
                        (limit,),
                    ):
                        out.append(
                            ArtifactRecord(
                                artifact_type="android.contact",
                                record={
                                    "contact_id": row["ROWID"],
                                    "display_name": row["display_name"],
                                    "value": None,
                                    "mimetype": None,
                                },
                                provenance=Provenance(
                                    source_logical_path=logical,
                                    source_real_path=str(db_path),
                                    source_sha256=digest,
                                ),
                                quality=Quality(confidence=0.8),
                            )
                        )
        finally:
            conn.close()
        return out
