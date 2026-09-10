"""
Android Excavator — parse Android folder dumps (read-only).

Point at a folder from adb pull, a nandroid extract, or similar.
No device connection required for parsing. Evidence DBs opened mode=ro.

Not a lockscreen cracker (see LockBreaker / Diamond Forger).
Not an iOS tool (see iDriller).
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["FolderDump", "ArtifactRecord", "run_extract", "list_parsers"]

from android_excavator.core.models import ArtifactRecord, Provenance
from android_excavator.core.source import FolderDump
from android_excavator.core.engine import run_extract, list_parsers
