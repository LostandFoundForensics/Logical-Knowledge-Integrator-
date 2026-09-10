from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class HashJob:
    format_id: str
    hash_line: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobResult:
    mode: str  # dry_run | dictionary
    format_id: str
    accepted: bool
    message: str
    recovered: bool = False
    plaintext: Optional[str] = None
    attempts: int = 0
    authority_recorded: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # never force plaintext into logs if empty
        if not d.get("plaintext"):
            d.pop("plaintext", None)
        return d
