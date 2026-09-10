"""
Sundial — Redaction
Consistent with Ghostframe: redactions are proven via SHA-256 of the original
value, never by exposing the value. The reader can mask phone numbers and hide
message contents on export.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Pattern

from sundial.core.audit import sha256_text


@dataclass(frozen=True)
class RedactionRule:
    name: str
    pattern: Pattern[str]
    label: str


# Phone numbers: international and common national formats, conservative.
_PHONE = re.compile(
    r"\+?\d[\d\s().-]{6,}\d"
)
_EMAIL = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)


def number_rules() -> List[RedactionRule]:
    return [
        RedactionRule("phone_number", _PHONE, "[REDACTED_NUMBER]"),
        RedactionRule("email", _EMAIL, "[REDACTED_EMAIL]"),
    ]


def redact_string(s: str, rules: List[RedactionRule]) -> Tuple[str, List[Dict[str, Any]]]:
    events: List[Dict[str, Any]] = []
    out = s
    for rule in rules:
        for m in rule.pattern.finditer(out):
            events.append({
                "rule": rule.name,
                "original_sha256": sha256_text(m.group(0)),
                "replacement": rule.label,
            })
        out = rule.pattern.sub(rule.label, out)
    return out, events


def redact_obj(obj: Any, rules: List[RedactionRule],
               hide_contents: bool = False,
               content_keys: Tuple[str, ...] = ("text", "body", "message", "content")
               ) -> Tuple[Any, List[Dict[str, Any]]]:
    """
    Recursively redact strings. When hide_contents is True, any dict key in
    content_keys has its entire value replaced (and ledgered).
    """
    events: List[Dict[str, Any]] = []

    if isinstance(obj, str):
        return redact_string(obj, rules)

    if isinstance(obj, list):
        out_list = []
        for item in obj:
            v, ev = redact_obj(item, rules, hide_contents, content_keys)
            out_list.append(v)
            events.extend(ev)
        return out_list, events

    if isinstance(obj, dict):
        out_dict: Dict[str, Any] = {}
        for k, v in obj.items():
            if hide_contents and k in content_keys and isinstance(v, str) and v:
                events.append({
                    "rule": "hide_contents",
                    "field": k,
                    "original_sha256": sha256_text(v),
                    "replacement": "[CONTENT_HIDDEN]",
                })
                out_dict[k] = "[CONTENT_HIDDEN]"
            else:
                vv, ev = redact_obj(v, rules, hide_contents, content_keys)
                out_dict[k] = vv
                events.extend(ev)
        return out_dict, events

    return obj, events


def summarize_redactions(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_rule: Dict[str, int] = {}
    for ev in events:
        by_rule[ev["rule"]] = by_rule.get(ev["rule"], 0) + 1
    return {
        "total_redactions": len(events),
        "by_rule": by_rule,
        "note": "Ledger stores SHA-256 of each original value, not the value itself.",
    }
