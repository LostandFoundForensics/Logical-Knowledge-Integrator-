from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


@dataclass
class FileEntry:
    relative_path: str
    size_bytes: int
    mtime_epoch: Optional[float]
    mode_octal: str
    is_dir: bool
    sha256: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionInfo:
    index: int
    start_lba: int
    size_lba: int
    type_hint: str
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageProbe:
    path: str
    size_bytes: int
    scheme: str  # gpt | mbr | none | unknown
    block_size: int
    partitions: List[PartitionInfo] = field(default_factory=list)
    fs_hints: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "scheme": self.scheme,
            "block_size": self.block_size,
            "partitions": [p.to_dict() for p in self.partitions],
            "fs_hints": list(self.fs_hints),
            "notes": list(self.notes),
        }
