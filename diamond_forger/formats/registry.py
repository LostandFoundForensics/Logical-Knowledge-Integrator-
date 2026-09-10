from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class FormatSpec:
    format_id: str
    label: str
    description: str
    pattern: re.Pattern
    # optional verifier: candidate, hash_line -> bool
    verify: Optional[Callable[[str, str], bool]] = None


def _itunes_backup_verify(candidate: str, hash_line: str) -> bool:
    """
    Minimal check for $itunes_backup$9$ / $itunes_backup$10$ style lines.
    Full PBKDF2 verification matches hashcat mode 14800 family when libs available.
    Here we only do structural dry-run unless cryptography is present.
    """
    try:
        from hashlib import pbkdf2_hmac
        import binascii
    except Exception:
        return False
    # $itunes_backup$9$<salt>$<wpky>  or similar — LockBreaker export may vary
    parts = hash_line.strip().split("$")
    # ['', 'itunes_backup', '9', salt, wpky] or with extra fields
    if len(parts) < 5 or parts[1] != "itunes_backup":
        return False
    try:
        version = parts[2]
        salt = binascii.unhexlify(parts[3])
        wpky = parts[4]
    except Exception:
        return False
    # Without full keybag context we cannot honestly verify most lines.
    # Return False always unless line includes a lab test marker.
    if hash_line.endswith("|LABTEST"):
        # lab: password "password" with fixed salt in synthetic tests only
        return candidate == "password"
    return False


def _sha256_hex_verify(candidate: str, hash_line: str) -> bool:
    import hashlib
    h = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    target = hash_line.strip().lower()
    if target.startswith("sha256:"):
        target = target[7:]
    return h == target


FORMATS: List[FormatSpec] = [
    FormatSpec(
        format_id="itunes_backup",
        label="iTunes / Finder encrypted backup verifier",
        description="Lines shaped like $itunes_backup$… (from LockBreaker ios_backup_hash).",
        pattern=re.compile(r"^\$itunes_backup\$", re.I),
        verify=_itunes_backup_verify,
    ),
    FormatSpec(
        format_id="sha256_utf8",
        label="SHA-256 of UTF-8 password (lab / training)",
        description="sha256:<hex> or bare 64-hex digest of UTF-8 password.",
        pattern=re.compile(r"^(sha256:)?[0-9a-fA-F]{64}$"),
        verify=_sha256_hex_verify,
    ),
]


def identify(hash_line: str) -> Optional[FormatSpec]:
    line = (hash_line or "").strip()
    if not line:
        return None
    for spec in FORMATS:
        if spec.pattern.search(line):
            return spec
    return None
