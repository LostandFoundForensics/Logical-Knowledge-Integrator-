from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from .base import Extractor, ExtractorContext, ExtractorResult
from .wrap_2john import run_2john
from .passthrough_hashfile import PassThroughHashFile


class IOSKeychainExtractorV1(Extractor):
    """
    Extracts crackable material from an iOS keychain database.
    Requires pairing record / lockdown access established beforehand
    (enforced via Access Surface activation check).
    """
    extractor_id = "extract_ios_keychain_hash_v1"
    required_surface_id = "IOS-PAIRING-LOCKDOWN"

    def run(self, ctx: ExtractorContext, params: Dict[str, Any]) -> ExtractorResult:
        # Validate access surface was activated
        activated = params.get("activated_access_surfaces", [])
        if self.required_surface_id not in activated:
            return ExtractorResult(
                ok=False,
                extractor_id=self.extractor_id,
                message=f"Access surface '{self.required_surface_id}' not activated. "
                        "Complete Phase 0 Access Surface Survey before proceeding.",
                errors=[f"PLAN_SURFACE_VIOLATION: {self.required_surface_id} required"],
            )

        # Keychain file candidates
        keychain_rel = params.get("keychain_path_relative", "Library/Keychains/keychain-2.db")
        tool_candidates = [
            "keychain2john",
            "keychain_dump2john",
        ]
        target = ctx.evidence_path / keychain_rel
        return run_2john(
            ctx=ctx,
            tool_candidates=tool_candidates,
            input_path=target,
            output_filename="ios_keychain.hash",
            extra_args=None,
        )


class AndroidPatternExtractorV1(Extractor):
    """
    Extracts Android pattern lock hash for offline cracking.
    Pattern hash is stored as gesture.key (SHA1 of pattern node sequence).
    """
    extractor_id = "extract_android_pattern_hash_v1"

    # Known paths for pattern/password hash on Android
    PATTERN_PATHS = [
        "data/system/gesture.key",
        "data/system/gatekeeper.gesture.key",
        "data/system/locksettings.db",  # newer Android stores in DB
    ]

    def run(self, ctx: ExtractorContext, params: Dict[str, Any]) -> ExtractorResult:
        # Try each known pattern hash location
        for rel in self.PATTERN_PATHS:
            candidate = ctx.evidence_path / rel
            if candidate.exists():
                # gesture.key is a raw SHA1 binary — convert to john-compatible hex hash
                if rel.endswith(".key"):
                    return self._handle_gesture_key(ctx, candidate, rel)
                elif rel.endswith(".db"):
                    return self._handle_locksettings_db(ctx, candidate, rel)

        return ExtractorResult(
            ok=False,
            extractor_id=self.extractor_id,
            message="No Android pattern lock hash file found in evidence.",
            errors=[f"Searched: {self.PATTERN_PATHS}"],
        )

    def _handle_gesture_key(self, ctx: ExtractorContext, key_path: Path, rel: str) -> ExtractorResult:
        """
        gesture.key is a 20-byte raw SHA1 of the node sequence.
        John's 'android-pattern' format expects: hash (hex).
        """
        from .common import sha256_file
        raw = key_path.read_bytes()
        if len(raw) != 20:
            return ExtractorResult(
                ok=False,
                extractor_id=self.extractor_id,
                message=f"gesture.key is {len(raw)} bytes (expected 20). Format unexpected.",
                errors=["gesture.key size mismatch"],
            )

        hex_hash = raw.hex()
        out_path = ctx.artifacts_dir / "android_pattern.hash"
        out_path.write_text(hex_hash + "\n", encoding="utf-8")
        digest = sha256_file(out_path)

        return ExtractorResult(
            ok=True,
            extractor_id=self.extractor_id,
            message=f"Extracted Android pattern SHA1 from {rel}",
            crack_input_path=str(out_path),
            crack_input_sha256=digest,
            produced_artifacts=[{"path": str(out_path), "sha256": digest, "kind": "crack_input"}],
            metadata={"source": rel, "format": "android_pattern_sha1_hex"},
        )

    def _handle_locksettings_db(self, ctx: ExtractorContext, db_path: Path, rel: str) -> ExtractorResult:
        """Extract from locksettings.db (newer Android)."""
        import sqlite3
        from .common import sha256_file
        try:
            # Source evidence (locksettings.db) — read-only
            uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
            con = sqlite3.connect(uri, uri=True, timeout=5.0)
            try:
                con.execute("PRAGMA query_only = ON")
            except Exception:
                pass
            cur = con.cursor()
            # Common keys: 'lockscreen.password_type', 'password_history_hash_factor'
            cur.execute(
                "SELECT value FROM locksettings WHERE name='lockscreen.password_salt' LIMIT 1"
            )
            row = cur.fetchone()
            con.close()
            if not row:
                return ExtractorResult(
                    ok=False,
                    extractor_id=self.extractor_id,
                    message="locksettings.db found but no pattern hash located.",
                    errors=["lockscreen.password_salt not found"],
                )
            out_path = ctx.artifacts_dir / "android_pattern.hash"
            out_path.write_text(str(row[0]) + "\n", encoding="utf-8")
            digest = sha256_file(out_path)
            return ExtractorResult(
                ok=True,
                extractor_id=self.extractor_id,
                message="Extracted pattern lock salt from locksettings.db",
                crack_input_path=str(out_path),
                crack_input_sha256=digest,
                produced_artifacts=[{"path": str(out_path), "sha256": digest, "kind": "crack_input"}],
            )
        except Exception as e:
            return ExtractorResult(
                ok=False,
                extractor_id=self.extractor_id,
                message="Failed to read locksettings.db",
                errors=[str(e)],
            )
