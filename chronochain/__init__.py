"""
ChronoChain — unified forensic timeline for LoKi Platform.

Ingest events from many sources, store them, correlate nearby events,
export a simple timeline a non-expert can read.

Philosophy: manual-first · observations only · plain language.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "TimelineEvent",
    "Timestamp",
    "TimelineStore",
    "build_links",
    "CorrelationConfig",
]

from chronochain.core.schema import TimelineEvent, Timestamp, Provenance
from chronochain.store import TimelineStore
from chronochain.correlation import build_links, CorrelationConfig
