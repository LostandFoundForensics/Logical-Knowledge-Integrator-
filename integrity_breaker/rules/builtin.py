"""
Built-in indicator rules.

These are *review heuristics*, not definitive malware verdicts.
Patterns are intentionally conservative and documented.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class IOCRule:
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: float
    match_type: str  # contains | regex
    target: str  # path | content
    patterns: tuple
    tags: tuple = ()
    enabled: bool = True
    notes: str = "Indicator only — requires examiner validation."


def builtin_rules() -> List[IOCRule]:
    return [
        IOCRule(
            rule_id="path.suspicious_agent",
            title="Path contains launch agent/daemon-like name",
            description="Path segment often associated with persistence on desktop OS dumps.",
            severity="medium",
            confidence=0.4,
            match_type="contains",
            target="path",
            patterns=("LaunchAgents", "LaunchDaemons", "launchd"),
            tags=("persistence", "path"),
        ),
        IOCRule(
            rule_id="path.ssh_authorized_keys",
            title="authorized_keys present",
            description="SSH authorized_keys file found under the tree.",
            severity="info",
            confidence=0.6,
            match_type="contains",
            target="path",
            patterns=("authorized_keys",),
            tags=("access", "path"),
        ),
        IOCRule(
            rule_id="path.tor_or_proxy_hint",
            title="Path suggests Tor/proxy tooling name",
            description="Filename or path contains tor/proxy-related strings.",
            severity="low",
            confidence=0.35,
            match_type="contains",
            target="path",
            patterns=("/tor/", "torrc", "proxychains"),
            tags=("network", "path"),
        ),
        IOCRule(
            rule_id="content.base64_long",
            title="Long base64-like blob in text file",
            description="Heuristic: long base64 alphabet run in a small text file.",
            severity="low",
            confidence=0.3,
            match_type="regex",
            target="content",
            patterns=(r"[A-Za-z0-9+/]{120,}={0,2}",),
            tags=("encoding", "content"),
            notes="Very high false-positive rate in normal data — review context.",
        ),
        IOCRule(
            rule_id="content.suspicious_url_scheme",
            title="Non-http URL scheme in text",
            description="Looks for file:// or custom schemes sometimes used in phishing payloads.",
            severity="low",
            confidence=0.35,
            match_type="regex",
            target="content",
            patterns=(r"\bfile://[^\s\"']+", r"\bms-msdt:", r"\bjavascript:"),
            tags=("url", "content"),
        ),
        IOCRule(
            rule_id="path.ios_profile",
            title="iOS configuration profile path",
            description="Mobileconfig / profile path under backup or dump.",
            severity="info",
            confidence=0.5,
            match_type="contains",
            target="path",
            patterns=(".mobileconfig", "ConfigurationProfiles"),
            tags=("ios", "path"),
        ),
        IOCRule(
            rule_id="path.android_magisk_hint",
            title="Path suggests Magisk/root tooling name",
            description="Path contains magisk/supersu-like strings.",
            severity="medium",
            confidence=0.45,
            match_type="contains",
            target="path",
            patterns=("magisk", "supersu", "SuperSU"),
            tags=("android", "root", "path"),
        ),
    ]
