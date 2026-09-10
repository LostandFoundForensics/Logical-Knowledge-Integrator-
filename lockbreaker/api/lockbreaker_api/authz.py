from __future__ import annotations
from fastapi import HTTPException
from .models import JobRequest

VALID_BASES = {"consent", "warrant", "court_order", "owner_recovery", "other"}

# Profiles that require elevated authority (no consent-only)
HIGH_AUTHORITY_PROFILES = {
    "ios_keychain",
    "android_pattern",
}

def validate_authorization(req: JobRequest) -> None:
    """Hard gate: no valid authorization = no run. Raises HTTPException."""

    if not req.authorization:
        raise HTTPException(403, "Authorization block is required.")

    if not req.authorization.reference_id or len(req.authorization.reference_id.strip()) < 3:
        raise HTTPException(403, "Authorization reference_id is required and must be meaningful.")

    if req.authorization.basis not in VALID_BASES:
        raise HTTPException(403, f"Invalid authorization basis: {req.authorization.basis}")

    # Elevated profiles require warrant or court_order
    if req.attack_profile in HIGH_AUTHORITY_PROFILES:
        if req.authorization.basis not in {"warrant", "court_order"}:
            raise HTTPException(
                403,
                f"Profile '{req.attack_profile}' requires warrant or court_order authorization. "
                f"Received: '{req.authorization.basis}'"
            )

    # Evidence integrity check
    if not req.evidence.sha256 or len(req.evidence.sha256.strip()) < 32:
        raise HTTPException(400, "Evidence SHA256 is required and must be at least 32 characters.")
