"""
Doctrine profiles — what LockBreaker is allowed to attempt, and under what authority.

Plain-language names. Minimum authorization basis is explicit.
Profiles never invent capabilities the platform does not have.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Profile:
    profile_id: str
    label: str
    description: str
    platform: str                    # ios | android | generic
    min_auth_basis: str              # consent | warrant | court_order | owner_request
    required_surfaces: tuple         # surface_ids that must be available
    extractors: tuple
    attack_strategies: tuple         # wordlist | pin_4 | pin_6 | pattern | dry_run_only
    risk_level: str                  # low | medium | high
    notes: str = ""


PROFILES: Dict[str, Profile] = {}


def _reg(p: Profile) -> Profile:
    PROFILES[p.profile_id] = p
    return p


_reg(Profile(
    profile_id="survey_only",
    label="Access surface survey only",
    description="Look for lawful entry points. Never attempts recovery.",
    platform="generic",
    min_auth_basis="consent",
    required_surfaces=(),
    extractors=(),
    attack_strategies=("dry_run_only",),
    risk_level="low",
    notes="Always safe. Run this first on every case.",
))

_reg(Profile(
    profile_id="ios_backup_hash",
    label="iOS encrypted backup password",
    description="Recover the password that protects an iTunes/Finder encrypted backup.",
    platform="ios",
    min_auth_basis="consent",
    required_surfaces=("IOS-BACKUP-PRESENT",),
    extractors=("ios_backup_manifest",),
    attack_strategies=("wordlist", "dry_run_only"),
    risk_level="medium",
    notes="Requires an encrypted backup file and authorization to attempt recovery.",
))

_reg(Profile(
    profile_id="android_pin_4",
    label="Android 4-digit PIN",
    description="Attempt recovery of a 4-digit screen lock PIN from extracted hash material.",
    platform="android",
    min_auth_basis="consent",
    required_surfaces=("ANDROID-FOLDER-DUMP",),
    extractors=("android_locksettings",),
    attack_strategies=("pin_4", "dry_run_only"),
    risk_level="medium",
    notes="Version-aware extract classifies legacy vs Gatekeeper vs synthetic password.",
))

_reg(Profile(
    profile_id="android_pin_6",
    label="Android 6-digit PIN",
    description="Attempt recovery of a 6-digit screen lock PIN from extracted hash material.",
    platform="android",
    min_auth_basis="consent",
    required_surfaces=("ANDROID-FOLDER-DUMP",),
    extractors=("android_locksettings",),
    attack_strategies=("pin_6", "dry_run_only"),
    risk_level="medium",
    notes="Version-aware extract classifies legacy vs Gatekeeper vs synthetic password.",
))

_reg(Profile(
    profile_id="android_pattern",
    label="Android pattern lock",
    description="Attempt recovery of a pattern lock from gesture key / Gatekeeper / locksettings material.",
    platform="android",
    min_auth_basis="warrant",
    required_surfaces=("ANDROID-FOLDER-DUMP",),
    extractors=("android_pattern", "android_locksettings"),
    attack_strategies=("pattern", "dry_run_only"),
    risk_level="high",
    notes="Higher sensitivity — warrant-level basis required by doctrine.",
))

_reg(Profile(
    profile_id="generic_hash",
    label="Generic hash (wordlist)",
    description="Authorized wordlist attack against an already-extracted hash file.",
    platform="generic",
    min_auth_basis="consent",
    required_surfaces=("HASH-FILE-PRESENT",),
    extractors=("passthrough_hash",),
    attack_strategies=("wordlist", "dry_run_only"),
    risk_level="medium",
))


def list_profiles() -> List[Profile]:
    return list(PROFILES.values())


def get_profile(profile_id: str) -> Profile:
    if profile_id not in PROFILES:
        known = ", ".join(sorted(PROFILES))
        raise KeyError(f"Unknown profile '{profile_id}'. Known: {known}")
    return PROFILES[profile_id]
