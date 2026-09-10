"""
Authorization gate — nothing beyond survey without a real reference.

Bases: owner_request | consent | warrant | court_order
High-risk profiles require warrant or court_order.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from lockbreaker.doctrine.profiles import Profile

VALID_BASES: FrozenSet[str] = frozenset(
    {"owner_request", "consent", "warrant", "court_order"}
)

HIGH_AUTH_BASES: FrozenSet[str] = frozenset({"warrant", "court_order"})


@dataclass(frozen=True)
class Authorization:
    basis: str
    reference_id: str
    examiner: str
    notes: str = ""

    def validate_basic(self) -> None:
        if self.basis not in VALID_BASES:
            raise PermissionError(
                f"Invalid authorization basis '{self.basis}'. "
                f"Use one of: {', '.join(sorted(VALID_BASES))}"
            )
        if not self.reference_id or len(self.reference_id.strip()) < 4:
            raise PermissionError(
                "Authorization reference_id is required (min 4 characters). "
                "Example: case number, warrant number, or consent form ID."
            )
        if not self.examiner or len(self.examiner.strip()) < 2:
            raise PermissionError("Examiner name is required.")


def require_authorization(auth: Authorization, profile: Profile) -> None:
    """Raise PermissionError if this profile may not run under this auth."""
    auth.validate_basic()
    if profile.risk_level == "high" and auth.basis not in HIGH_AUTH_BASES:
        raise PermissionError(
            f"Profile '{profile.profile_id}' is high risk and requires "
            f"warrant or court_order (got '{auth.basis}')."
        )
    # Hierarchy: court_order > warrant > consent > owner_request
    order = ["owner_request", "consent", "warrant", "court_order"]
    need = order.index(profile.min_auth_basis)
    have = order.index(auth.basis)
    if have < need:
        raise PermissionError(
            f"Profile '{profile.profile_id}' requires at least "
            f"'{profile.min_auth_basis}' (got '{auth.basis}')."
        )
