"""
Android lock material extraction — version-aware (read-only on evidence).

Classifies what the dump actually contains:

  legacy_pattern   — gesture.key (typically 20-byte SHA-1 of pattern)
  legacy_password  — password.key (SHA-1 || MD5 of salted credential) + salt
  gatekeeper       — gatekeeper.password.key / gatekeeper.pattern.key (scrypt handle)
  synthetic        — locksettings hints at sp-handle / synthetic password (Android 9+)
  hardware_backed  — indicators that offline attack may be impossible

Does not crack. Writes structured material into the case workspace only.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PASSWORD_TYPE_LABELS = {
    0: "none_or_unknown",
    65536: "pattern",
    131072: "numeric_pin",
    196608: "numeric_complex",
    262144: "alphabetic",
    327680: "alphanumeric",
}


def _open_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        conn.execute("PRAGMA query_only = ON")
    except Exception:
        pass
    conn.execute("SELECT 1")
    return conn


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_files(root: Path, names: Tuple[str, ...], limit: int = 20) -> List[Path]:
    found: List[Path] = []
    for name in names:
        for p in root.rglob(name):
            if p.is_file():
                found.append(p)
                if len(found) >= limit:
                    return found
    return found


def read_locksettings_map(db_path: Path) -> Dict[str, str]:
    conn = _open_ro(db_path)
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "locksettings" not in tables:
            return {}
        cols = {r[1] for r in conn.execute('PRAGMA table_info("locksettings")')}
        if "name" in cols and "value" in cols:
            rows = conn.execute("SELECT name, value FROM locksettings").fetchall()
            return {str(n): ("" if v is None else str(v)) for n, v in rows}
        return {}
    finally:
        conn.close()


def classify_gatekeeper_blob(data: bytes) -> Dict[str, Any]:
    """
    Software Gatekeeper password_handle layout (publicly documented default):
      version   : 1 byte
      user_id   : 8 bytes
      flags     : 8 bytes
      salt      : 8 bytes
      signature : 32 bytes
    Total often 57 bytes.
    """
    info: Dict[str, Any] = {
        "size": len(data),
        "format": "unknown",
        "version": None,
        "salt_hex": None,
        "signature_hex": None,
        "hardware_backed_best_effort": None,
        "notes": [],
    }
    if len(data) == 0:
        info["notes"].append("Empty key file.")
        return info

    if len(data) >= 57:
        version = data[0]
        salt = data[17:25]
        signature = data[25:57]
        info["version"] = version
        info["salt_hex"] = salt.hex()
        info["signature_hex"] = signature.hex()
        info["format"] = "gatekeeper_password_handle_v_software"
        if len(data) > 57:
            info["notes"].append("Blob longer than classic 57-byte software handle.")
        info["hardware_backed_best_effort"] = False
    elif len(data) == 20:
        info["format"] = "possible_sha1_digest"
        info["signature_hex"] = data.hex()
        info["notes"].append("20-byte blob — may be legacy SHA-1 style, not Gatekeeper.")
    else:
        info["format"] = "unrecognized"
        info["signature_hex"] = data.hex()
        info["notes"].append(
            "Size does not match classic software Gatekeeper handle (57 bytes)."
        )
        info["hardware_backed_best_effort"] = True
        info["notes"].append(
            "Treating as possibly hardware-backed or OEM-custom — offline recovery uncertain."
        )
    return info


def classify_legacy_password_key(data: bytes) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "size": len(data),
        "format": "unknown",
        "sha1_hex": None,
        "md5_hex": None,
    }
    text = None
    try:
        text = data.decode("ascii").strip()
    except Exception:
        text = None

    if text and len(text) >= 72 and all(c in "0123456789abcdefABCDEF" for c in text[:72]):
        info["format"] = "legacy_password_sha1_md5_hex"
        info["sha1_hex"] = text[:40].lower()
        info["md5_hex"] = text[40:72].lower()
    elif len(data) >= 36:
        info["format"] = "legacy_password_sha1_md5_raw"
        info["sha1_hex"] = data[:20].hex()
        info["md5_hex"] = data[20:36].hex()
    elif len(data) == 20:
        info["format"] = "legacy_sha1_only"
        info["sha1_hex"] = data.hex()
    else:
        info["format"] = "unrecognized"
    return info


def extract_android_lock_bundle(dump_root: Path, out_dir: Path) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(dump_root)

    report: Dict[str, Any] = {
        "ok": False,
        "extractor": "android_lock_versioned",
        "era": "unknown",
        "credential_kinds_seen": [],
        "artifacts": [],
        "locksettings": {},
        "files": {},
        "offline_recovery_outlook": "unknown",
        "message": "",
        "warnings": [],
    }

    ls_hits = _find_files(root, ("locksettings.db",))
    settings: Dict[str, str] = {}
    if ls_hits:
        try:
            settings = read_locksettings_map(ls_hits[0])
            report["files"]["locksettings.db"] = str(ls_hits[0])
        except Exception as e:
            report["warnings"].append(f"locksettings.db read failed: {e}")

    salt = settings.get("lockscreen.password_salt") or ""
    type_raw = (
        settings.get("lockscreen.password_type")
        or settings.get("lockscreen.password_type_alternate")
        or ""
    )
    type_label = "unknown"
    try:
        type_label = PASSWORD_TYPE_LABELS.get(int(type_raw), f"raw:{type_raw}")
    except Exception:
        if type_raw:
            type_label = f"raw:{type_raw}"

    sp_handle = settings.get("sp-handle") or settings.get("sp_handle") or ""
    interesting = {
        k: v
        for k, v in settings.items()
        if any(
            s in k.lower()
            for s in (
                "password", "pattern", "salt", "lockscreen",
                "gatekeeper", "sp-handle", "sp_handle", "synthetic",
            )
        )
    }
    report["locksettings"] = {
        "keys_interesting": interesting,
        "password_type_label": type_label,
        "password_type_raw": type_raw,
        "salt": salt,
        "sp_handle": sp_handle,
    }

    ls_out = out_dir / "locksettings_extract.json"
    ls_out.write_text(json.dumps(report["locksettings"], indent=2), encoding="utf-8")
    report["artifacts"].append(
        {
            "path": str(ls_out),
            "sha256": _sha256_file(ls_out),
            "kind": "locksettings_extract",
        }
    )

    eras_found: List[str] = []
    kinds: List[str] = []

    gesture_hits = _find_files(root, ("gesture.key",))
    if gesture_hits:
        data = gesture_hits[0].read_bytes()
        dest = out_dir / "legacy_gesture.key.hex"
        dest.write_text(data.hex() + "\n", encoding="utf-8")
        report["files"]["gesture.key"] = str(gesture_hits[0])
        report["artifacts"].append(
            {
                "path": str(dest),
                "sha256": _sha256_file(dest),
                "kind": "legacy_gesture_hash",
                "size": len(data),
            }
        )
        eras_found.append("legacy_pattern")
        kinds.append("pattern_legacy")
        meta = {
            "era": "pre_gatekeeper_pattern",
            "size": len(data),
            "typical": "20-byte SHA-1 of pattern indices on older Android",
            "hash_hex": data.hex(),
        }
        (out_dir / "legacy_gesture_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    pw_hits = _find_files(root, ("password.key",))
    if pw_hits:
        data = pw_hits[0].read_bytes()
        info = classify_legacy_password_key(data)
        dest = out_dir / "legacy_password.key.hex"
        dest.write_text(data.hex() + "\n", encoding="utf-8")
        report["files"]["password.key"] = str(pw_hits[0])
        report["artifacts"].append(
            {
                "path": str(dest),
                "sha256": _sha256_file(dest),
                "kind": "legacy_password_hash",
                "format": info["format"],
            }
        )
        eras_found.append("legacy_password")
        kinds.append("password_legacy")
        hashcat_line = None
        if info.get("md5_hex") and salt:
            hashcat_line = f"{info['md5_hex']}:{salt}"
            hl = out_dir / "legacy_password_hashcat.txt"
            hl.write_text(hashcat_line + "\n", encoding="utf-8")
            report["artifacts"].append(
                {
                    "path": str(hl),
                    "sha256": _sha256_file(hl),
                    "kind": "legacy_password_hashcat",
                }
            )
        meta = {**info, "salt_from_locksettings": salt, "hashcat_line": hashcat_line}
        (out_dir / "legacy_password_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    gk_pass = _find_files(root, ("gatekeeper.password.key",))
    gk_pat = _find_files(root, ("gatekeeper.pattern.key", "gatekeeper.gesture.key"))
    for label, hits, kind in (
        ("gatekeeper.password.key", gk_pass, "password_gatekeeper"),
        ("gatekeeper.pattern.key", gk_pat, "pattern_gatekeeper"),
    ):
        if not hits:
            continue
        data = hits[0].read_bytes()
        info = classify_gatekeeper_blob(data)
        dest = out_dir / f"{label}.hex"
        dest.write_text(data.hex() + "\n", encoding="utf-8")
        report["files"][label] = str(hits[0])
        report["artifacts"].append(
            {
                "path": str(dest),
                "sha256": _sha256_file(dest),
                "kind": "gatekeeper_blob",
                "credential": kind,
                "format": info["format"],
            }
        )
        eras_found.append("gatekeeper")
        kinds.append(kind)
        if info.get("hardware_backed_best_effort"):
            report["warnings"].append(
                f"{label}: possibly hardware-backed or OEM-custom — offline recovery uncertain."
            )
        meta_path = out_dir / f"{label}.meta.json"
        meta_path.write_text(json.dumps(info, indent=2), encoding="utf-8")
        report["artifacts"].append(
            {
                "path": str(meta_path),
                "sha256": _sha256_file(meta_path),
                "kind": "gatekeeper_meta",
            }
        )

    if sp_handle:
        eras_found.append("synthetic_password")
        kinds.append("synthetic_password_pointer")
        report["warnings"].append(
            "sp-handle present — Android 9+ synthetic password path. "
            "Full offline unlock often needs spblob / TEE material not in a simple key file."
        )
        spblobs = list(root.rglob("*.spblob"))[:10]
        report["files"]["spblobs_found"] = [str(p) for p in spblobs]
        if spblobs:
            report["warnings"].append(
                f"Found {len(spblobs)} .spblob file(s) — record only; not decrypted here."
            )

    if not eras_found and not settings:
        report["message"] = "No locksettings.db or known lock key files under dump root."
        report["offline_recovery_outlook"] = "none"
        return report

    if "legacy_pattern" in eras_found or "legacy_password" in eras_found:
        outlook = "possible_offline"
    elif "gatekeeper" in eras_found:
        if any("uncertain" in w.lower() or "hardware" in w.lower() for w in report["warnings"]):
            outlook = "uncertain_hw_or_oem"
        else:
            outlook = "possible_offline_scrypt_gatekeeper"
    elif "synthetic_password" in eras_found:
        outlook = "limited_without_tee_material"
    else:
        outlook = "metadata_only"

    seen = set()
    eras_u = []
    for e in eras_found:
        if e not in seen:
            seen.add(e)
            eras_u.append(e)

    report["ok"] = True
    report["era"] = "+".join(eras_u) if eras_u else "locksettings_only"
    report["credential_kinds_seen"] = kinds
    report["offline_recovery_outlook"] = outlook
    report["message"] = (
        f"Android lock extraction complete. Era={report['era']}. "
        f"Outlook={outlook}. Types={', '.join(kinds) or 'none'}."
    )

    summary_path = out_dir / "android_lock_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "era": report["era"],
                "outlook": outlook,
                "kinds": kinds,
                "password_type_label": type_label,
                "warnings": report["warnings"],
                "files": report["files"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    report["artifacts"].append(
        {
            "path": str(summary_path),
            "sha256": _sha256_file(summary_path),
            "kind": "android_lock_summary",
        }
    )
    return report


def extract_locksettings(dump_root: Path, out_dir: Path) -> Dict[str, Any]:
    return extract_android_lock_bundle(dump_root, out_dir)


def extract_gesture_key(dump_root: Path, out_dir: Path) -> Dict[str, Any]:
    full = extract_android_lock_bundle(dump_root, out_dir)
    kinds = full.get("credential_kinds_seen") or []
    if any("pattern" in k for k in kinds):
        return full
    if not full.get("ok"):
        return full
    full = dict(full)
    full["message"] = full.get("message", "") + " (pattern-specific blob optional)"
    return full
