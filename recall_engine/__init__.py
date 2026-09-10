"""
Recall Engine — iOS artifact depth from standard backups (read-only).

iLEAPP-class coverage for LoKi: notes, Safari history, and related
databases resolved via Manifest.db.

Basic SMS / calls / contacts remain in **iDriller**.
Recall Engine extends the same backup layout with more artifact types.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["scan_backup", "list_parsers"]

from recall_engine.core.engine import scan_backup, list_parsers
