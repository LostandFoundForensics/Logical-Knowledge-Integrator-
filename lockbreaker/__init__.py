"""
LockBreaker — Access Surface Orchestrator

Not a blind password cracker.
First finds *lawful* ways in (pairing, backups, ADB, extracted hashes).
Only then — with explicit authorization — attempts credential recovery.

Doctrine:
  Phase 0  Survey access surfaces (always safe, always first)
  Phase 1  Extract crackable material from authorized surfaces
  Phase 2  Recovery attempt (dry-run by default; real backends opt-in)

Manual-first · Authorized use only · Full audit ledger · Never fabricates results
"""
from __future__ import annotations

__version__ = "2.0.0"
__all__ = [
    "survey_access_surfaces",
    "list_profiles",
    "run_job",
    "Authorization",
]

from lockbreaker.surfaces.survey import survey_access_surfaces
from lockbreaker.doctrine.profiles import list_profiles
from lockbreaker.orchestrator import run_job
from lockbreaker.auth.gate import Authorization
