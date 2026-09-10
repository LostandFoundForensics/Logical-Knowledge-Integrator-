from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any


def classify_finding(item: str, value: str, method: str) -> Dict[str, Any]:
    """
    Enriches a raw finding with complexity assessment, pattern classification,
    and court-ready notes. Never modifies the recovered value itself.
    """
    complexity = _assess_complexity(value)
    pattern = _classify_pattern(value)
    court_note = _court_note(complexity, pattern, method)

    return {
        "item": item,
        "value": value,
        "method": method,
        "complexity": complexity,
        "pattern_class": pattern,
        "court_note": court_note,
        "recovered_at": datetime.now(timezone.utc).isoformat(),
    }


def _assess_complexity(pw: str) -> str:
    if not pw:
        return "unknown"
    length = len(pw)
    has_upper = any(c.isupper() for c in pw)
    has_lower = any(c.islower() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    has_special = any(not c.isalnum() for c in pw)
    variety = sum([has_upper, has_lower, has_digit, has_special])

    if length < 4:
        return "trivial"
    if length <= 6 and variety <= 1:
        return "very_low"
    if length <= 8 and variety <= 2:
        return "low"
    if length <= 12 and variety <= 3:
        return "medium"
    if length > 12 and variety >= 3:
        return "high"
    return "medium"


def _classify_pattern(pw: str) -> str:
    if not pw:
        return "unknown"
    if pw.isdigit():
        if len(pw) == 4:
            return "numeric_pin_4"
        if len(pw) == 6:
            return "numeric_pin_6"
        return "numeric"
    if pw.isalpha():
        return "alpha_only"
    if pw.isalnum():
        return "alphanumeric"
    # Check for common patterns
    import re
    if re.match(r"^[A-Za-z]+\d{2,4}[!@#$]?$", pw):
        return "word_plus_digits"
    if re.match(r"^\d{4}[A-Za-z]+$", pw):
        return "digits_plus_word"
    if re.match(r"^[A-Za-z]\w+[!@#$%^&*]+$", pw):
        return "word_with_special_suffix"
    return "mixed"


def _court_note(complexity: str, pattern: str, method: str) -> str:
    notes = []

    if complexity in ("trivial", "very_low"):
        notes.append(
            "The recovered password is of low complexity. "
            "This is consistent with commonly used personal passwords."
        )
    elif complexity == "high":
        notes.append(
            "The recovered password is of high complexity. "
            "Recovery required targeted attack methods."
        )

    if pattern == "numeric_pin_4":
        notes.append(
            "The password consists of a 4-digit numeric PIN — "
            "a common format for mobile device screen locks."
        )
    elif pattern == "numeric_pin_6":
        notes.append(
            "The password consists of a 6-digit numeric PIN."
        )
    elif pattern == "word_plus_digits":
        notes.append(
            "The password follows a common human-memorable pattern: "
            "a word followed by a numeric sequence."
        )

    notes.append(
        f"Recovered using method: {method}. "
        "Recovery does not imply authorization beyond the scope of this examination."
    )

    return " ".join(notes)


def normalize_findings_tsv(output_path: Path, method: str, redaction_mode: str) -> List[Dict[str, Any]]:
    """
    Reads tab-separated findings file and returns classified finding dicts.
    Format: item<TAB>value (one per line)
    """
    findings: List[Dict[str, Any]] = []
    if not output_path or not Path(output_path).exists():
        return findings

    for line in Path(output_path).read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        parts = line.split("\t", 1)
        item = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else ""

        if not item or not value:
            continue

        findings.append(classify_finding(item, value, method))

    return findings
