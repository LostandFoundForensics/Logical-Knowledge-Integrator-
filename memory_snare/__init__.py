"""
Memory Snare — Android artifact parsing from folder dumps (read-only).

ALEAPP-class *depth* for LoKi: accounts, browser history, Wi-Fi configs,
and other app/system databases under an extracted tree.

Acquisition-oriented flows live in **Android Excavator**.
Memory Snare focuses on broader artifact coverage from the same dump style.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["scan_dump", "list_parsers"]

from memory_snare.core.engine import scan_dump, list_parsers
