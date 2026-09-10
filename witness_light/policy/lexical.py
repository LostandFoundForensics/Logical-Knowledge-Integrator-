"""
Fail-closed lexical policy.

Blocks common intent / causation / guilt phrasing in draft text.
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Intentionally simple; examiner can still write carefully by hand.
FORBIDDEN_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("intent", re.compile(r"\b(intent(?:ionally)?|motive|guilty|innocent)\b", re.I)),
    ("causation", re.compile(r"\b(therefore (?:they|he|she|the suspect)|proves that|this shows that)\b", re.I)),
    ("behavior_conclusion", re.compile(r"\b(must have|obviously|clearly committed|perpetrator)\b", re.I)),
    ("absolute_claim", re.compile(r"\b(beyond (?:any )?doubt|irrefutable)\b", re.I)),
]


def check_text(text: str) -> List[str]:
    """Return list of policy violation labels (empty if clean)."""
    hits = []
    for label, pat in FORBIDDEN_PATTERNS:
        if pat.search(text or ""):
            hits.append(label)
    return hits


def sanitize_or_flag(text: str) -> Tuple[str, List[str]]:
    violations = check_text(text)
    return text, violations
