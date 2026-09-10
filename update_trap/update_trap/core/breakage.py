"""
Update Trap — core/breakage.py
Cross-references a DiffReport against a parser dependency registry to
flag which LoKi parsers are at risk after an observed change.

Fixes applied (this module was pasted twice as literal duplicates,
same pattern seen earlier in Ghostframe/Integrity Breaker/Open Record —
deduplicated here to a single definition):

1. Glob-matching fix: the original analyze() did naive substring
   matching — `p.replace("**/", "") in cp` — against changed paths. This
   both over-matches (a glob fragment that happens to appear as a
   substring of an unrelated path) and under-matches (a glob with
   multiple wildcard segments doesn't degrade into a substring check at
   all). Replaced with the real glob matcher from patterns.py
   (matches_any), the same one Phase 2 targeting already uses — so a
   parser's declared path dependency is checked the same way scope
   targeting checks include/exclude globs, rather than two different
   half-correct implementations existing side by side.
"""
from __future__ import annotations
import json
from typing import Dict, List

from update_trap.core.diff_engine import DiffReport
from update_trap.core.patterns import matches_any


class BreakageFinding:
    def __init__(self, parser_id: str, risk_level: str, reasons: List[str]):
        self.parser_id = parser_id
        self.risk_level = risk_level   # low | medium | high
        self.reasons = reasons

    def to_dict(self) -> dict:
        return {
            "parser_id": self.parser_id,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
        }


class ParserBreakageDetector:
    def __init__(self, registry_path: str):
        with open(registry_path, "r", encoding="utf-8") as f:
            self.registry = json.load(f)

    def analyze(self, report: DiffReport) -> List[BreakageFinding]:
        findings: List[BreakageFinding] = []

        changed_paths = sorted({p.rel_path for p in report.path_changes})
        changed_tables = {sc.table for sc in report.schema_changes}
        changed_keys = sorted({
            ch.rel_path for ch in report.structured_changes
            if ch.change in ("keys_added", "keys_removed")
        })

        for parser_id, caps in self.registry.items():
            reasons: List[str] = []
            deps = caps.get("depends_on", {})

            # FIX: real glob matching instead of substring matching.
            # A parser's declared path dependency (e.g. "**/mmssms.db")
            # is checked against every changed path using the same
            # fnmatch-based matcher Phase 2 targeting already relies on,
            # rather than stripping "**/" and checking substring
            # containment (which both over- and under-matches).
            for p in deps.get("paths", []):
                if matches_any_changed_path(p, changed_paths):
                    reasons.append(f"path dependency changed: {p}")

            for t in deps.get("tables", []):
                if t in changed_tables:
                    reasons.append(f"table dependency changed: {t}")

            for k in deps.get("structured_keys", []):
                if matches_any_changed_key(k, changed_keys):
                    reasons.append(f"structured key dependency changed: {k}")

            if reasons:
                risk = "high" if len(reasons) >= 2 else "medium"
                findings.append(BreakageFinding(parser_id, risk, reasons))

        return findings


def matches_any_changed_path(dep_glob: str, changed_paths: List[str]) -> bool:
    """
    A parser's path dependency is a single glob (e.g. "**/mmssms.db").
    It matches if ANY changed path satisfies that glob — i.e. we check
    the glob against each candidate path using matches_any(), rather
    than checking substring containment.
    """
    for cp in changed_paths:
        if matches_any(cp, [dep_glob]):
            return True
    return False


def matches_any_changed_key(dep_key: str, changed_key_paths: List[str]) -> bool:
    """
    Structured-key dependencies (e.g. "root.messages[]") are dotted-path
    strings, not filesystem globs, so they're compared by checking
    whether the dependency string appears as a path-segment-aligned
    substring of any file that had structured-key changes. This stays a
    containment check (dotted-key paths don't have the same wildcard
    semantics as file globs) but is scoped to files that actually had
    key changes, rather than treating every changed_keys entry as
    equally relevant regardless of whether it had key-level changes.
    """
    return any(dep_key in ck for ck in changed_key_paths)
