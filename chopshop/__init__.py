"""
Chop Shop — portable LoKi workbench (Santoku-class role).

Creates a standard case bench, checks which LoKi tools import cleanly,
and records an environment profile. It does not replace Autopsy or a
full Linux distro — it is the staging area where operators work.

Evidence outside the bench is never modified.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["create_bench", "probe_environment", "list_stations"]

from chopshop.core.bench import create_bench, list_stations
from chopshop.core.probe import probe_environment
