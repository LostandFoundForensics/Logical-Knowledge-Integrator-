"""
Pattern Harvester — bulk identifier extraction from files and folders.

Scans evidence *read-only* for emails, phones, URLs, IPv4, and common tokens.
Writes findings only to a case output folder.

Like bulk_extractor in spirit: find structured strings, do not interpret guilt.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["scan_path", "list_scanners", "Finding"]

from pattern_harvester.core.models import Finding
from pattern_harvester.core.engine import scan_path, list_scanners
