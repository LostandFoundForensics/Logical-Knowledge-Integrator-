from __future__ import annotations
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

# Real ed25519 signing via PyNaCl
# pip install pynacl
try:
    from nacl.signing import SigningKey, VerifyKey
    from nacl.exceptions import BadSignatureError
    _NACL_AVAILABLE = True
except ImportError:
    _NACL_AVAILABLE = False

# Key management:
# - In production: load from HSM or secure vault
# - In dev: generated once and stored in LOCKBREAKER_SIGNING_KEY_HEX env var
# - NEVER commit the private key

_KEY_ENV = "LOCKBREAKER_SIGNING_KEY_HEX"
_KEY_FILE = Path(os.environ.get("LOCKBREAKER_KEY_FILE", "/etc/lockbreaker/signing.key"))

def _load_or_generate_key() -> bytes:
    """Load signing key from env, file, or generate ephemeral dev key."""
    hex_key = os.environ.get(_KEY_ENV)
    if hex_key:
        return bytes.fromhex(hex_key)
    if _KEY_FILE.exists():
        return bytes.fromhex(_KEY_FILE.read_text().strip())
    # Dev fallback: generate ephemeral key and warn loudly
    import warnings
    warnings.warn(
        "LOCKBREAKER: No signing key found. Using ephemeral dev key. "
        "Signatures will NOT be verifiable across restarts. "
        f"Set {_KEY_ENV} env var or place key at {_KEY_FILE}",
        RuntimeWarning,
        stacklevel=2,
    )
    if _NACL_AVAILABLE:
        return bytes(SigningKey.generate())
    return os.urandom(32)

_SIGNING_KEY_BYTES: bytes = _load_or_generate_key()

def get_verify_key_b64() -> str:
    """Returns the public verify key as base64 — safe to share/publish."""
    if not _NACL_AVAILABLE:
        return "nacl_not_installed"
    sk = SigningKey(_SIGNING_KEY_BYTES)
    return base64.b64encode(bytes(sk.verify_key)).decode()

def sign_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produces a court-grade signed result.
    Uses ed25519 if PyNaCl is available, falls back to HMAC-SHA256 with clear labeling.
    """
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    now = datetime.now(timezone.utc).isoformat()

    if _NACL_AVAILABLE:
        sk = SigningKey(_SIGNING_KEY_BYTES)
        signed = sk.sign(payload)
        sig_b64 = base64.b64encode(signed.signature).decode()
        verify_key_b64 = base64.b64encode(bytes(sk.verify_key)).decode()
        alg = "ed25519"
    else:
        # HMAC-SHA256 fallback — still integrity-protected but not asymmetric
        import hmac, hashlib
        sig_bytes = hmac.new(_SIGNING_KEY_BYTES, payload, hashlib.sha256).digest()
        sig_b64 = base64.b64encode(sig_bytes).decode()
        verify_key_b64 = "hmac_sha256_symmetric_key_not_shareable"
        alg = "hmac-sha256-fallback (install pynacl for ed25519)"

    return {
        **result,
        "audit": {
            **(result.get("audit") or {}),
            "signed_at": now,
            "signature": sig_b64,
            "signature_alg": alg,
            "verify_key": verify_key_b64,
            "signer_id": "lockbreaker-signer-v1",
        }
    }

def verify_result(signed_result: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifies a signed result. Returns (ok, message).
    Anyone with the public verify_key can run this.
    """
    if not _NACL_AVAILABLE:
        return False, "PyNaCl not installed — cannot verify ed25519 signature"

    audit = signed_result.get("audit", {})
    sig_b64 = audit.get("signature")
    verify_key_b64 = audit.get("verify_key")
    alg = audit.get("signature_alg", "")

    if "ed25519" not in alg:
        return False, f"Cannot verify algorithm: {alg}"

    if not sig_b64 or not verify_key_b64:
        return False, "Missing signature or verify_key in audit block"

    # Reconstruct payload (same as signing — without audit block)
    result_without_audit = {k: v for k, v in signed_result.items() if k != "audit"}
    payload = json.dumps(result_without_audit, sort_keys=True, separators=(",", ":")).encode("utf-8")

    try:
        vk = VerifyKey(base64.b64decode(verify_key_b64))
        sig = base64.b64decode(sig_b64)
        vk.verify(payload, sig)
        return True, "Signature verified successfully"
    except BadSignatureError:
        return False, "Signature INVALID — result may have been tampered with"
    except Exception as e:
        return False, f"Verification error: {e}"
