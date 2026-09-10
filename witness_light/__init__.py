"""
Witness Light — non-destructive report drafting for LoKi cases.

Reads *exports* (Bardo timeline, tool JSONL). Never opens original evidence.
Draft language is constrained to: Observed | Context | Consistent With | Limitation | Unknown.

No automatic findings of guilt or intent.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["draft_report", "list_sentence_classes"]

from witness_light.core.engine import draft_report, list_sentence_classes
