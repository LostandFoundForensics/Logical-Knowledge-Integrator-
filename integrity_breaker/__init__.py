"""
Integrity Breaker — indicator / IOC scan over folder dumps (read-only).

MVT-class *spirit*: look for path and content patterns that warrant human
review. Hits are indicators, not proof of compromise.

Never modifies evidence. Never claims “device is infected” automatically.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["scan_path", "list_rules"]

from integrity_breaker.core.engine import scan_path, list_rules
