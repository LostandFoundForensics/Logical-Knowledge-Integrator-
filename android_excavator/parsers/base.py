from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from android_excavator.core.models import ArtifactRecord
from android_excavator.core.source import FolderDump


@dataclass(frozen=True)
class ParserInfo:
    parser_id: str
    label: str
    description: str
    category: str  # communications | people | web | system


class Parser(ABC):
    info: ParserInfo

    @abstractmethod
    def parse(self, dump: FolderDump, *, limit: int = 50_000) -> List[ArtifactRecord]:
        ...
