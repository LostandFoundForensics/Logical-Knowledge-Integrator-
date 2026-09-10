"""
Plugin contract for Ghostframe.

Every analysis step is a plugin with a clear id, human label, and run().
Operators pick by label; the engine runs the plugin against a RunContext.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PluginSpec:
    """What the operator sees."""
    plugin_id: str
    label: str                    # short plain-language name
    description: str              # one sentence: what this looks for
    category: str = "general"     # processes | network | files | malware | os
    requires_volatility: bool = False
    os_hints: tuple = ()          # e.g. ("windows", "linux") — empty = any


@dataclass
class RunContext:
    """
    Everything a plugin needs about the evidence under analysis.
    Evidence path is never written to.
    """
    evidence_path: str
    evidence_sha256: str
    case_id: str = ""
    output_dir: str = ""
    os_hint: str = ""             # optional: windows|linux|mac|unknown
    options: Dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        return Path(self.evidence_path)


@dataclass
class PluginResult:
    ok: bool
    plugin_id: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    row_count: int = 0

    def __post_init__(self) -> None:
        if self.row_count == 0 and self.rows:
            self.row_count = len(self.rows)


class GhostframePlugin(ABC):
    """Base class for all Ghostframe analysis plugins."""

    spec: PluginSpec

    @abstractmethod
    def run(self, ctx: RunContext) -> PluginResult:
        """Observe only. Never modify evidence."""
        ...
