from __future__ import annotations
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


# ── Wordlist registry ─────────────────────────────────────────────────────────
# Maps logical IDs to asset paths. Loaded from manifest in production.
WORDLIST_REGISTRY: Dict[str, str] = {
    "WL-MOBILE-US-2025-01":    "/opt/lockbreaker/wordlists/mobile_us_2025.txt",
    "WL-LIFECYCLE-US-2025-01": "/opt/lockbreaker/wordlists/lifecycle_us_2025.txt",
    "WL-GENERIC-MOBILE":       "/opt/lockbreaker/wordlists/generic_mobile.txt",
    "WL-ROCKYOU-2024":         "/opt/lockbreaker/wordlists/rockyou_2024.txt",
    "WL-OWNER-DERIVED":        "/opt/lockbreaker/wordlists/owner_derived_runtime.txt",
    "WL-ANDROID-PIN-4":        "/opt/lockbreaker/wordlists/pins_4digit.txt",
    "WL-ANDROID-PIN-6":        "/opt/lockbreaker/wordlists/pins_6digit.txt",
    "WL-ANDROID-PATTERN":      "/opt/lockbreaker/wordlists/android_patterns.txt",
    "WL-NUMERIC-DATES":        "/opt/lockbreaker/wordlists/numeric_dates.txt",
}

RULESET_REGISTRY: Dict[str, str] = {
    "RD-IOS-BEHAVIOR-01":   "/opt/lockbreaker/rulesets/ios_behavior_01.rules",
    "RD-NUMERIC-EXPANSION": "/opt/lockbreaker/rulesets/numeric_expansion.rules",
    "RD-MOBILE-COMMON":     "/opt/lockbreaker/rulesets/mobile_common.rules",
    "RD-LEET-BASIC":        "/opt/lockbreaker/rulesets/leet_basic.rules",
    "RD-APPEND-SPECIAL":    "/opt/lockbreaker/rulesets/append_special.rules",
}


def generate_owner_wordlist(confirmed_context: Dict[str, Any], out_path: Path) -> Optional[str]:
    """
    Generates a context-derived mini-wordlist from confirmed examiner inputs.
    Written to artifacts dir for use in Phase 1.
    Returns path if generated, None if no useful context.
    """
    name = confirmed_context.get("owner_name", "").strip()
    year = str(confirmed_context.get("year_hint", "")).strip()
    lifecycle_hints = confirmed_context.get("lifecycle_hints", [])

    if not name and not year:
        return None

    lines = set()

    if name:
        variants = [
            name, name.lower(), name.upper(), name.capitalize(),
            name[:3].lower(), name[:4].lower(),
        ]
        for v in variants:
            lines.add(v)
            if year:
                lines.add(f"{v}{year}")
                lines.add(f"{v}{year[-2:]}")
                lines.add(f"{year}{v}")
            lines.add(f"{v}1")
            lines.add(f"{v}12")
            lines.add(f"{v}123")
            lines.add(f"{v}!")
            lines.add(f"{v}#")
            lines.add(f"{v}@")

    if year:
        lines.add(year)
        lines.add(year[-2:])
        for h in lifecycle_hints:
            lines.add(f"{year}holiday")
            lines.add(f"holiday{year}")

    if not lines:
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(sorted(lines)), encoding="utf-8")
    return str(out_path)


def compose_strategy(
    profile_id: str,
    confirmed_context: Dict[str, Any],
    max_runtime_minutes: int = 1440,
) -> Dict[str, Any]:
    """
    AKE core: translates profile intent + human context into a phased strategy.
    Each phase has a goal, wordlists, rulesets, and a runtime budget.
    The strategy feeds AST (translator) for execution planning.
    """
    owner_name = confirmed_context.get("owner_name")
    locale = confirmed_context.get("locale", "en-US")
    year_hint = confirmed_context.get("year_hint")
    lifecycle_hints = confirmed_context.get("lifecycle_hints", [])
    platform = confirmed_context.get("platform", "ios")

    has_owner = bool(owner_name)
    has_year = bool(year_hint)

    # ── Profile-specific strategy composition ─────────────────────────────────

    if profile_id == "ios_encrypted_backup":
        phases = _build_ios_backup_phases(has_owner, has_year, locale, lifecycle_hints, max_runtime_minutes)
        context_factors = _context_factors(has_owner, locale, lifecycle_hints)
        confidence = 0.75 if has_owner else 0.55

    elif profile_id == "ios_keychain":
        phases = _build_ios_keychain_phases(has_owner, max_runtime_minutes)
        context_factors = ["ios_device", "keychain_target"]
        confidence = 0.65

    elif profile_id in ("android_encrypted_backup",):
        phases = _build_android_backup_phases(has_owner, has_year, max_runtime_minutes)
        context_factors = _context_factors(has_owner, locale, lifecycle_hints)
        confidence = 0.70 if has_owner else 0.50

    elif profile_id == "android_pin_4digit":
        phases = [_pin_phase(4, max_runtime_minutes)]
        context_factors = ["android_pin", "4_digit_space"]
        confidence = 0.98  # exhaustive — will find it if the format is right

    elif profile_id == "android_pin_6digit":
        phases = [_pin_phase(6, max_runtime_minutes)]
        context_factors = ["android_pin", "6_digit_space"]
        confidence = 0.98

    elif profile_id == "android_pattern":
        phases = [_pattern_phase(max_runtime_minutes)]
        context_factors = ["android_pattern_lock"]
        confidence = 0.90

    elif profile_id in ("generic_hash_wordlist_rules", "app_sqlite_encrypted"):
        phases = _build_generic_phases(has_owner, locale, max_runtime_minutes)
        context_factors = ["generic_hash"]
        confidence = 0.60 if has_owner else 0.45

    else:
        phases = _build_generic_phases(has_owner, locale, max_runtime_minutes)
        context_factors = ["unknown_profile"]
        confidence = 0.40

    # Add owner-derived wordlist as Phase 0 if we have enough context
    if has_owner or has_year:
        phases.insert(0, {
            "phase": 0,
            "goal": "Context-derived candidate sweep",
            "wordlists": ["WL-OWNER-DERIVED"],
            "rulesets": ["RD-IOS-BEHAVIOR-01", "RD-NUMERIC-EXPANSION"],
            "expected_runtime": "minutes",
            "rationale": "Targets passwords derived from device owner's name, important dates, and lifecycle patterns.",
        })

    # Re-number phases
    for i, p in enumerate(phases):
        p["phase"] = i

    strategy = {
        "strategy_id": f"STR-{profile_id.upper()[:8]}-{uuid.uuid4().hex[:6].upper()}",
        "profile_id": profile_id,
        "confidence": confidence,
        "context_factors": context_factors,
        "confirmed_context_used": {k: bool(v) for k, v in confirmed_context.items()},
        "phases": phases,
        "stop_conditions": ["password_recovered", "time_limit_reached"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    strategy["strategy_digest_sha256"] = _digest(strategy)
    return strategy


# ── Phase builders ────────────────────────────────────────────────────────────

def _build_ios_backup_phases(
    has_owner: bool, has_year: bool, locale: str,
    lifecycle: List[str], total_minutes: int
) -> List[Dict[str, Any]]:
    phases = []
    remaining = total_minutes

    # Phase: locale-biased mobile wordlist + iOS behavioral rules
    locale_wl = "WL-MOBILE-US-2025-01" if "US" in locale else "WL-GENERIC-MOBILE"
    t1 = min(60, remaining)
    phases.append({
        "goal": "Common mobile password + iOS behavior rules",
        "wordlists": [locale_wl],
        "rulesets": ["RD-IOS-BEHAVIOR-01", "RD-MOBILE-COMMON"],
        "expected_runtime": "minutes",
        "rationale": f"Targets most common iOS backup passwords in {locale} locale.",
        "phase_budget_minutes": t1,
    })
    remaining -= t1

    if remaining > 0:
        t2 = min(180, remaining)
        phases.append({
            "goal": "Lifecycle + date expansion",
            "wordlists": ["WL-LIFECYCLE-US-2025-01", "WL-NUMERIC-DATES"],
            "rulesets": ["RD-NUMERIC-EXPANSION", "RD-APPEND-SPECIAL"],
            "expected_runtime": "hours",
            "rationale": "Targets passwords derived from significant dates, life events, and year-based patterns.",
            "phase_budget_minutes": t2,
        })
        remaining -= t2

    if remaining > 0:
        phases.append({
            "goal": "Broad generic fallback",
            "wordlists": ["WL-ROCKYOU-2024", "WL-GENERIC-MOBILE"],
            "rulesets": ["RD-LEET-BASIC", "RD-MOBILE-COMMON"],
            "expected_runtime": "bounded",
            "rationale": "Broader coverage using curated breach-derived wordlists.",
            "phase_budget_minutes": remaining,
        })

    return phases

def _build_ios_keychain_phases(has_owner: bool, total_minutes: int) -> List[Dict[str, Any]]:
    return [{
        "goal": "Keychain password recovery (device passcode correlation)",
        "wordlists": ["WL-ANDROID-PIN-4", "WL-ANDROID-PIN-6", "WL-MOBILE-US-2025-01"],
        "rulesets": ["RD-IOS-BEHAVIOR-01"],
        "expected_runtime": "hours",
        "rationale": "iOS keychain passwords often correlate with device passcode or simple personal passwords.",
        "phase_budget_minutes": total_minutes,
    }]

def _build_android_backup_phases(has_owner: bool, has_year: bool, total_minutes: int) -> List[Dict[str, Any]]:
    t1 = min(90, total_minutes)
    phases = [{
        "goal": "Android mobile common + behavior rules",
        "wordlists": ["WL-GENERIC-MOBILE", "WL-MOBILE-US-2025-01"],
        "rulesets": ["RD-MOBILE-COMMON", "RD-NUMERIC-EXPANSION"],
        "expected_runtime": "hours",
        "rationale": "Android backup passwords follow similar patterns to iOS but with more numeric bias.",
        "phase_budget_minutes": t1,
    }]
    remaining = total_minutes - t1
    if remaining > 0:
        phases.append({
            "goal": "Broad fallback",
            "wordlists": ["WL-ROCKYOU-2024"],
            "rulesets": ["RD-LEET-BASIC"],
            "expected_runtime": "bounded",
            "rationale": "Broader coverage.",
            "phase_budget_minutes": remaining,
        })
    return phases

def _pin_phase(digits: int, total_minutes: int) -> Dict[str, Any]:
    space = 10 ** digits
    return {
        "goal": f"Exhaustive {digits}-digit PIN sweep ({space:,} candidates)",
        "wordlists": [f"WL-ANDROID-PIN-{digits}"],
        "rulesets": [],
        "expected_runtime": "minutes" if digits == 4 else "hours",
        "rationale": f"Complete numeric search space for {digits}-digit PINs. Exhaustive — will succeed if format is correct.",
        "phase_budget_minutes": total_minutes,
    }

def _pattern_phase(total_minutes: int) -> Dict[str, Any]:
    return {
        "goal": "Android pattern lock sweep",
        "wordlists": ["WL-ANDROID-PATTERN"],
        "rulesets": [],
        "expected_runtime": "minutes",
        "rationale": "Pattern locks have a bounded search space; this phase covers all common complexity levels.",
        "phase_budget_minutes": total_minutes,
    }

def _build_generic_phases(has_owner: bool, locale: str, total_minutes: int) -> List[Dict[str, Any]]:
    return [{
        "goal": "Generic wordlist + rules",
        "wordlists": ["WL-GENERIC-MOBILE", "WL-ROCKYOU-2024"],
        "rulesets": ["RD-MOBILE-COMMON", "RD-LEET-BASIC"],
        "expected_runtime": "bounded",
        "rationale": "Standard wordlist+rules recovery for generic hashes.",
        "phase_budget_minutes": total_minutes,
    }]

def _context_factors(has_owner: bool, locale: str, lifecycle: List[str]) -> List[str]:
    factors = []
    if has_owner: factors.append("owner_name_known")
    if locale: factors.append(f"locale_{locale.replace('-','_').lower()}")
    for h in lifecycle: factors.append(f"lifecycle_{h}")
    return factors

def _digest(obj: Dict[str, Any]) -> str:
    clean = {k: v for k, v in obj.items() if k != "strategy_digest_sha256"}
    return hashlib.sha256(
        json.dumps(clean, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
