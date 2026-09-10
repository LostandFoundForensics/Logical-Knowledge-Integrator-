"""Chrome / Chromium history on Android (read-only).

Chrome timestamps are microseconds since 1601-01-01 UTC (Windows epoch).
We convert to unix milliseconds and label the original format.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from android_excavator.core.models import ArtifactRecord, Provenance, Quality
from android_excavator.core.source import FolderDump
from android_excavator.core.sqlite_ro import open_evidence_ro
from android_excavator.parsers.base import Parser, ParserInfo

# Chrome epoch: 1601-01-01 → Unix epoch offset in microseconds
CHROME_EPOCH_OFFSET_US = 11_644_473_600_000_000


def chrome_time_to_unix_ms(chrome_us: Optional[int]) -> Optional[int]:
    if chrome_us is None:
        return None
    try:
        v = int(chrome_us)
        if v <= 0:
            return None
        return int((v - CHROME_EPOCH_OFFSET_US) / 1000)
    except Exception:
        return None


class ChromeHistoryParser(Parser):
    info = ParserInfo(
        parser_id="chrome",
        label="Chrome web history",
        description="Reads visited URLs and titles from Chrome History databases.",
        category="web",
    )

    def parse(self, dump: FolderDump, *, limit: int = 50_000) -> List[ArtifactRecord]:
        records: List[ArtifactRecord] = []
        paths = dump.find_by_name("History")
        paths += dump.find_path_contains("com.android.chrome")
        paths += dump.find_path_contains("com.chrome")
        # Deduplicate; History files often have no .db suffix
        seen = set()
        unique: List[Path] = []
        for p in paths:
            rp = p.resolve()
            if rp in seen:
                continue
            if p.name == "History" or p.suffix.lower() == ".db":
                seen.add(rp)
                unique.append(p)

        for db_path in unique:
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
            if "urls" not in tables:
                return out
            # urls: id, url, title, visit_count, last_visit_time
            cols = {r[1] for r in conn.execute('PRAGMA table_info("urls")')}
            if "url" not in cols:
                return out
            time_col = "last_visit_time" if "last_visit_time" in cols else None
            title_col = "title" if "title" in cols else None
            select = ["id", "url"]
            if title_col:
                select.append(title_col)
            if time_col:
                select.append(time_col)
            if "visit_count" in cols:
                select.append("visit_count")
            order = f'ORDER BY "{time_col}" DESC' if time_col else ""
            sql = f'SELECT {", ".join(select)} FROM urls {order} LIMIT ?'
            for row in conn.execute(sql, (limit,)):
                chrome_ts = row[time_col] if time_col else None
                unix_ms = chrome_time_to_unix_ms(chrome_ts)
                out.append(
                    ArtifactRecord(
                        artifact_type="android.chrome_history",
                        record={
                            "id": row["id"],
                            "url": row["url"],
                            "title": row[title_col] if title_col else None,
                            "visit_count": row["visit_count"] if "visit_count" in row.keys() else None,
                            "last_visit_chrome_us": chrome_ts,
                            "last_visit_unix_ms": unix_ms,
                        },
                        provenance=Provenance(
                            source_logical_path=logical,
                            source_real_path=str(db_path),
                            source_sha256=digest,
                        ),
                        quality=Quality(
                            confidence=0.9,
                            flags=["chrome_1601_epoch_converted"] if unix_ms else [],
                        ),
                    )
                )
        finally:
            conn.close()
        return out
