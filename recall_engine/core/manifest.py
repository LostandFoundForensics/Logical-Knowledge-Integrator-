"""Manifest.db index for iOS backups — read-only."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, List, Optional

from recall_engine.core.sqlite_ro import open_evidence_ro


class ManifestEntry:
    __slots__ = ("file_id", "domain", "relative_path", "flags")

    def __init__(self, file_id: str, domain: str, relative_path: str, flags: int = 0):
        self.file_id = file_id
        self.domain = domain
        self.relative_path = relative_path
        self.flags = flags


class ManifestIndex:
    def __init__(self, backup_root: Path) -> None:
        self.root = Path(backup_root).resolve()
        mp = self.root / "Manifest.db"
        if not mp.is_file():
            hits = list(self.root.glob("[Mm]anifest.db"))
            if not hits:
                raise FileNotFoundError(f"No Manifest.db in {self.root}")
            mp = hits[0]
        self.manifest_path = mp
        self._conn = open_evidence_ro(mp)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self) -> "ManifestIndex":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def iter_files(self) -> Iterator[ManifestEntry]:
        cur = self._conn.execute(
            "SELECT fileID, domain, relativePath, flags FROM Files"
        )
        for row in cur:
            fid = row["fileID"]
            if not fid:
                continue
            yield ManifestEntry(
                str(fid),
                str(row["domain"] or ""),
                str(row["relativePath"] or ""),
                int(row["flags"] or 0),
            )

    def find(
        self,
        *,
        contains: Optional[str] = None,
        endswith: Optional[str] = None,
        limit: int = 50,
    ) -> List[ManifestEntry]:
        out: List[ManifestEntry] = []
        for e in self.iter_files():
            if contains and contains not in e.relative_path:
                continue
            if endswith and not e.relative_path.endswith(endswith):
                continue
            out.append(e)
            if len(out) >= limit:
                break
        return out

    def resolve(self, file_id: str) -> Optional[Path]:
        if not file_id or len(file_id) < 2:
            return None
        for p in (self.root / file_id[:2] / file_id, self.root / file_id):
            if p.is_file():
                return p
        return None
