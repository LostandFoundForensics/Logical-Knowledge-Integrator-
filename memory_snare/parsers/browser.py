"""Chrome / browser History — Chrome 1601 epoch handled."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from memory_snare.core.discover import find_named, find_path_contains
from memory_snare.core.models import ArtifactHit
from memory_snare.core.sqlite_ro import open_evidence_ro
from memory_snare.parsers.base import Parser, ParserInfo

CHROME_EPOCH_OFFSET_US = 11_644_473_600_000_000


def chrome_to_unix_ms(v: Optional[int]) -> Optional[int]:
    if v is None:
        return None
    try:
        n = int(v)
        if n <= 0:
            return None
        return int((n - CHROME_EPOCH_OFFSET_US) / 1000)
    except Exception:
        return None


class BrowserHistoryParser(Parser):
    info = ParserInfo(
        parser_id="browser",
        label="Browser history",
        description="Chrome/WebView History databases (1601 epoch corrected).",
    )

    def parse(self, root: Path, *, limit: int = 20_000) -> List[ArtifactHit]:
        paths = find_named(root, ("History",))
        paths += find_path_contains(root, "com.android.chrome")
        paths += find_path_contains(root, "com.chrome")
        seen = set()
        unique = []
        for p in paths:
            if p.name == "History" or "history" in p.name.lower():
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
            if "urls" not in tables:
                return out
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
            order = f'ORDER BY "{time_col}" DESC' if time_col else ""
            sql = f'SELECT {", ".join(select)} FROM urls {order} LIMIT ?'
            for row in conn.execute(sql, (limit,)):
                raw_t = row[time_col] if time_col else None
                unix_ms = chrome_to_unix_ms(raw_t)
                url = row["url"]
                title = row[title_col] if title_col else None
                out.append(
                    ArtifactHit(
                        artifact_type="android.browser_visit",
                        summary=str(title or url)[:200],
                        record={
                            "url": url,
                            "title": title,
                            "last_visit_chrome_us": raw_t,
                            "last_visit_unix_ms": unix_ms,
                        },
                        source_path=str(db),
                        confidence=0.9,
                        flags=["chrome_1601_epoch"] if unix_ms else [],
                    )
                )
        finally:
            conn.close()
        return out
