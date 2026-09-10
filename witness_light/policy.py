"""
Witness Light — policy.py
Lexical enforcement layer. Fail closed on banned phrasing.
Fix #4: enforce_paragraph_policy() now returns new DraftParagraph objects
        rather than mutating in place — keeps the function pure and testable.
"""
from __future__ import annotations

import re
from typing import List

from models import SentenceClass, DraftParagraph

# ── Banned phrases (hard blocks) ─────────────────────────────────────────────
# These phrases assert intent, causality, or behavioral inference.
# None belong in forensic draft language.
BANNED_PHRASES = [
    "intended",
    "attempted",
    "planned",
    "likely",
    "probably",
    "motive",
    "indicates intent",
    "suggests intent",
    "behavior pattern",
    "pattern of life",
    "wanted to",
    "therefore",
    "led to",
    "resulted in",
    "culminated",
    "escalated",
]

BANNED_REGEX = [
    re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE)
    for p in BANNED_PHRASES
]


def assert_sentence_class_allowed(sentence_class: SentenceClass) -> None:
    """Only the five defined sentence classes are valid. Fail on anything else."""
    if sentence_class not in (
        SentenceClass.OBSERVED,
        SentenceClass.CONTEXT,
        SentenceClass.CONSISTENT_WITH,
        SentenceClass.LIMITATION,
        SentenceClass.UNKNOWN,
    ):
        raise ValueError(f"Invalid sentence class: {sentence_class}")


def redact_or_reject(text: str) -> str:
    """
    Fail closed if banned phrasing appears.
    Rejection is stronger than redaction for court-safe output.
    """
    for rx in BANNED_REGEX:
        m = rx.search(text or "")
        if m:
            raise ValueError(
                f"Output violates redline lexical policy. "
                f"Banned phrase detected: '{m.group(0)}'"
            )
    return text


def enforce_paragraph_policy(
    paragraphs: List[DraftParagraph],
) -> List[DraftParagraph]:
    """
    - Ensures only allowed sentence classes.
    - Ensures no banned wording.
    - Limitations and unknowns cannot be silently removed.

    FIX #4: Returns NEW DraftParagraph objects instead of mutating in place.
    The function is now pure — same input always produces same output,
    no side effects on the original list.
    """
    out: List[DraftParagraph] = []
    for p in paragraphs:
        assert_sentence_class_allowed(p.sentence_class)
        clean_text = redact_or_reject(p.text)
        out.append(
            DraftParagraph(
                sentence_class=p.sentence_class,
                text=clean_text,
                artifact_ids=list(p.artifact_ids),
                truthloom_dataset_ids=list(p.truthloom_dataset_ids),
                confidence=p.confidence,
            )
        )
    return out


def require_disclaimer(purpose_str: str) -> str:
    base = (
        "DRAFT — INVESTIGATOR REVIEW REQUIRED\n"
        "Witness Light is a read-only interpretation and drafting aid.\n"
        "It does not access, acquire, modify, parse, or analyze original evidence.\n"
        "All conclusions and opinions (if any) are those of the examiner.\n"
        "Events presented are ordered by timestamps only; no causality is asserted.\n"
    )
    if "Court-ready" in purpose_str:
        base += "Court-Ready Mode: conservative phrasing enforced; uncertainty preserved.\n"
    return base.strip()
