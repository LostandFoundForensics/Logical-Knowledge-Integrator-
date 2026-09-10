"""Safari History.db via Manifest — read-only."""
from __future__ import annotations

from typing import List

from recall_engine.core.manifest import ManifestIndex
from recall_engine.core.models import ArtifactHit
from recall_engine.core.sqlite_ro import open_evidence_ro
from recall_engine.core.timeutil import apple_to_unix_ms
from recall_engine.parsers.base import Parser, ParserInfo


class SafariHistoryParser(Parser):
    info = ParserInfo(
        parser_id="safari",
        label="Safari history",
        description="Visited URLs from Safari History.db.",
    )

    def parse(self, manifest: ManifestIndex, *, limit: int = 20_000) -> List[ArtifactHit]:
        entries = manifest.find(contains="History.db", limit=20)
        entries += manifest.find(endswith="History.db", limit=10)
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
            # history_items + history_visits common
            if "history_items" in tables:
                sql = """
                    SELECT hi.id AS id, hi.url AS url, hi.domain_expansion AS domain,
                           hv.visit_time AS visit_time, hv.title AS title
                    FROM history_items hi
                    LEFT JOIN history_visits hv ON hv.history_item = hi.id
                    ORDER BY hv.visit_time DESC
                    LIMIT ?
                """
                if "history_visits" not in tables:
                    sql = "SELECT id, url, domain_expansion AS domain, NULL AS visit_time, NULL AS title FROM history_items LIMIT ?"
                for row in conn.execute(sql, (limit,)):
                    url = row["url"]
                    title = row["title"]
                    vt = row["visit_time"]
                    unix_ms = apple_to_unix_ms(vt, unit="seconds")
                    out.append(
                        ArtifactHit(
                            artifact_type="ios.safari_visit",
                            summary=str(title or url or "")[:200],
                            record={
                                "url": url,
                                "title": title,
                                "visit_time_raw": vt,
                                "visit_unix_ms": unix_ms,
                            },
                            source_path=entry.relative_path,
                            domain=entry.domain,
                            file_id=entry.file_id,
                            confidence=0.9,
                        )
                    )
        finally:
            conn.close()
        return out
