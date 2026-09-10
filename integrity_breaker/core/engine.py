from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from integrity_breaker.core.models import Finding
from integrity_breaker.rules.builtin import IOCRule, builtin_rules

TEXT_EXTS = {
    ".log", ".txt", ".json", ".csv", ".xml", ".html", ".htm",
    ".plist", ".conf", ".ini", ".yaml", ".yml", ".cfg", ".js", ".css",
}


def list_rules() -> List[Dict[str, str]]:
    return [
        {
            "id": r.rule_id,
            "title": r.title,
            "severity": r.severity,
            "target": r.target,
            "description": r.description,
        }
        for r in builtin_rules()
        if r.enabled
    ]


def _match_path(rule: IOCRule, rel: str) -> Optional[str]:
    for pat in rule.patterns:
        if rule.match_type == "contains" and pat.lower() in rel.lower():
            return pat
        if rule.match_type == "regex":
            try:
                if re.search(pat, rel, re.I):
                    return pat
            except re.error:
                continue
    return None


def _match_content(rule: IOCRule, text: str) -> Optional[tuple]:
    for pat in rule.patterns:
        if rule.match_type == "contains":
            idx = text.lower().find(pat.lower())
            if idx >= 0:
                start = max(0, idx - 40)
                end = min(len(text), idx + len(pat) + 40)
                return pat, text[start:end].replace("\n", " ")
        if rule.match_type == "regex":
            try:
                m = re.search(pat, text, re.I | re.M)
            except re.error:
                continue
            if m:
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                return pat, text[start:end].replace("\n", " ")
    return None


def scan_path(
    root: str | Path,
    *,
    max_files: int = 20_000,
    max_file_bytes: int = 1_500_000,
    rule_ids: Optional[List[str]] = None,
) -> List[Finding]:
    root = Path(root).resolve()
    if not root.exists():
        raise FileNotFoundError(root)

    rules = [r for r in builtin_rules() if r.enabled]
    if rule_ids:
        wanted = set(rule_ids)
        rules = [r for r in rules if r.rule_id in wanted]

    findings: List[Finding] = []
    n = 0
    paths: Iterable[Path]
    if root.is_file():
        paths = [root]
    else:
        paths = root.rglob("*")

    for fp in paths:
        if n >= max_files:
            break
        if not fp.is_file():
            continue
        try:
            size = fp.stat().st_size
        except OSError:
            continue
        if size <= 0:
            continue
        n += 1
        try:
            rel = fp.relative_to(root).as_posix() if root.is_dir() else fp.name
        except ValueError:
            rel = str(fp)

        for rule in rules:
            if rule.target == "path":
                hit = _match_path(rule, rel)
                if hit:
                    findings.append(
                        Finding(
                            rule_id=rule.rule_id,
                            title=rule.title,
                            severity=rule.severity,
                            match_on="path",
                            matched=hit,
                            source_path=rel,
                            confidence=rule.confidence,
                            tags=list(rule.tags),
                            notes=rule.notes,
                        )
                    )

        # content rules only on text-like small files
        if size > max_file_bytes:
            continue
        suf = fp.suffix.lower()
        if suf and suf not in TEXT_EXTS:
            continue
        content_rules = [r for r in rules if r.target == "content"]
        if not content_rules:
            continue
        try:
            data = fp.read_bytes()[:max_file_bytes]
            text = data.decode("utf-8", errors="ignore")
        except OSError:
            continue
        for rule in content_rules:
            hit = _match_content(rule, text)
            if hit:
                pat, snippet = hit
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        title=rule.title,
                        severity=rule.severity,
                        match_on="content",
                        matched=pat if isinstance(pat, str) else str(pat),
                        source_path=rel,
                        snippet=snippet[:200],
                        confidence=rule.confidence,
                        tags=list(rule.tags),
                        notes=rule.notes,
                    )
                )
    return findings
