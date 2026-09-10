from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from recall_engine.core.manifest import ManifestIndex
from recall_engine.core.models import ArtifactHit


@dataclass(frozen=True)
class ParserInfo:
    parser_id: str
    label: str
    description: str


class Parser(ABC):
    info: ParserInfo

    @abstractmethod
    def parse(self, manifest: ManifestIndex, *, limit: int = 20_000) -> List[ArtifactHit]:
        ...
