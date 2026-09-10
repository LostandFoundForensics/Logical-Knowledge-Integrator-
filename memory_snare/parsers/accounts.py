"""System accounts database (accounts.db) — read-only."""
from __future__ import annotations

from pathlib import Path
from typing import List

from memory_snare.core.discover import find_named, find_path_contains
from memory_snare.core.models import ArtifactHit
from memory_snare.core.sqlite_ro import open_evidence_ro
from memory_snare.parsers.base import Parser, ParserInfo


class AccountsParser(Parser):
    info = ParserInfo(
        parser_id="accounts",
        label="System accounts",
        description="Reads accounts.db for account names and types.",
    )

    def parse(self, root: Path, *, limit: int = 20_000) -> List[ArtifactHit]:
        paths = find_named(root, ("accounts.db",))
        paths += find_path_contains(root, "com.android.providers.settings")
        paths = [p for p in paths if p.suffix.lower() == ".db"]
        # also common under system
        paths += find_path_contains(root, "accounts.db")
        seen = set()
        unique = []
        for p in paths:
            rp = p.resolve()
            if rp not in seen and p.is_file():
                seen.add(rp)
                unique.append(p)

        hits: List[ArtifactHit] = []
        for db in unique:
            try:
                hits.extend(self._parse_db(db, limit=limit - len(hits)))
            except Exception:
                continue
            if len(hits) >= limit:
                break
        return hits[:limit]

    def _parse_db(self, db: Path, *, limit: int) -> List[ArtifactHit]:
        out: List[ArtifactHit] = []
        conn = open_evidence_ro(db)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            table = "accounts" if "accounts" in tables else None
            if not table:
                return out
            cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
            name_col = next((c for c in ("name", "account_name") if c in cols), None)
            type_col = next((c for c in ("type", "account_type") if c in cols), None)
            if not name_col:
                return out
            select = [f'"{name_col}"']
            if type_col:
                select.append(f'"{type_col}"')
            sql = f'SELECT {", ".join(select)} FROM "{table}" LIMIT ?'
            for row in conn.execute(sql, (limit,)):
                name = row[name_col]
                atype = row[type_col] if type_col else None
                out.append(
                    ArtifactHit(
                        artifact_type="android.account",
                        summary=f"{name} ({atype})" if atype else str(name),
                        record={"name": name, "type": atype},
                        source_path=str(db),
                        confidence=0.9,
                    )
                )
        finally:
            conn.close()
        return out
