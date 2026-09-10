from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List

from memory_snare.core.models import ArtifactHit


@dataclass(frozen=True)
class ParserInfo:
    parser_id: str
    label: str
    description: str


class Parser(ABC):
    info: ParserInfo

    @abstractmethod
    def parse(self, root: Path, *, limit: int = 20_000) -> List[ArtifactHit]:
        ...
