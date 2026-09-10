"""
EchoReader — encrypted backup intake and readiness (read-only).

Inspects iOS backups (and simple Android backup headers) to answer:
  - Is this encrypted?
  - What can we do next without writing into evidence?
  - Should LockBreaker ios_backup_hash / iDriller run?

Decrypt is *never* the default. Real recovery stays in LockBreaker with authority.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["inspect_path", "list_checks"]

from echoreader.core.engine import inspect_path, list_checks
