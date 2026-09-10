"""
Bardo Engine — post-acquisition case brain for LoKi.

Ingest observations from Android Excavator, iDriller, ChronoChain, etc.
Store them in a *working* case database (never the evidence itself).
Correlate lightly. Export timelines and summaries.

Manual-first. Observations only — no automatic guilt narratives.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["CaseStore", "run_ingest", "list_sources"]

from bardo.core.store import CaseStore
from bardo.core.engine import run_ingest, list_sources
