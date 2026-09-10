"""
Dry-run recovery backend.

Honest: reports what *would* run, never fabricates a password.
This is the default. Real hashcat/john only when LOCKBREAKER_ENABLE_REAL_BACKENDS=1.
"""
from __future__ import annotations

from typing import Any, Dict, List


def run_dry_run(
    *,
    profile_id: str,
    strategy: str,
    artifacts: List[Dict[str, Any]],
    seed_candidates: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "found": False,
        "backend": "dry-run",
        "profile_id": profile_id,
        "strategy": strategy,
        "message": (
            "DRY-RUN only. No password was attempted or recovered. "
            "Set LOCKBREAKER_ENABLE_REAL_BACKENDS=1 and supply lawful authority "
            "to enable real recovery backends."
        ),
        "artifacts_seen": [a.get("path") for a in artifacts],
        "seed_candidates_count": len(seed_candidates or []),
        "findings": [],
        "near_misses": [],
    }
