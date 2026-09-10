"""
Diamond Forger — authorized hash recovery (doctrine-first).

Takes verifier lines produced by LockBreaker (and similar), validates format,
and optionally runs a *bounded* dictionary check.

Default mode is dry-run: no guessing. Real attempts require:
  - examiner identity
  - authority string
  - --execute

This is not a silent cracker and not a Hashcat replacement for GPU farms.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["validate_hash_line", "list_formats", "dry_run", "dictionary_check"]

from diamond_forger.core.engine import validate_hash_line, list_formats, dry_run, dictionary_check
