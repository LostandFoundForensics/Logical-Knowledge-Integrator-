"""
iOS encrypted backup — extract offline password-verifier material.

Reads Manifest.plist BackupKeyBag (TLV) and writes a hashcat-compatible
$hash line into the *case* workspace. Does not crack. Does not modify the backup.

Public hash forms (hashcat):
  $itunes_backup$*9*<wpky>*<iter>*<salt>**           # pre–iOS 10
  $itunes_backup$*10*<wpky>*<iter>*<salt>*<dpic>*<dpsl>  # iOS 10+

Hashcat modes (operator responsibility to match version):
  14700 ≈ iTunes backup < 10
  14800 ≈ iTunes backup 10.x+
"""
from __future__ import annotations

import hashlib
import json
import plistlib
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _parse_keybag_tlv(blob: bytes) -> List[Tuple[str, bytes]]:
    """
    Backup keybag is a sequence of TLV records:
      tag  : 4 bytes ASCII
      len  : 4 bytes big-endian uint32
      value: <len> bytes
    """
    entries: List[Tuple[str, bytes]] = []
    i = 0
    n = len(blob)
    while i + 8 <= n:
        tag = blob[i : i + 4]
        try:
            tag_s = tag.decode("ascii")
        except Exception:
            break
        (length,) = struct.unpack(">I", blob[i + 4 : i + 8])
        i += 8
        if length < 0 or i + length > n:
            break
        value = blob[i : i + length]
        i += length
        entries.append((tag_s, value))
    return entries


def _group_keybag(entries: List[Tuple[str, bytes]]) -> Dict[str, Any]:
    """
    Keybag layout: header tags, then repeated class-key blocks starting at UUID.
    We need header SALT/ITER/(DPIC/DPSL) and one WPKY used as password verifier.
    """
    header: Dict[str, bytes] = {}
    class_keys: List[Dict[str, bytes]] = []
    current: Optional[Dict[str, bytes]] = None

    header_tags = {"VERS", "TYPE", "UUID", "HMCK", "WRAP", "SALT", "ITER", "DPIC", "DPSL", "DPWT"}

    for tag, value in entries:
        if tag == "UUID" and current is not None:
            class_keys.append(current)
            current = {"UUID": value}
            continue
        if tag == "UUID" and "UUID" not in header and current is None:
            # First UUID often belongs to header block in some dumps; keep flexible
            if "SALT" not in header and "ITER" not in header:
                header["UUID"] = value
            else:
                current = {"UUID": value}
            continue
        if current is not None and tag in {"CLAS", "WRAP", "KTYP", "WPKY", "UUID"}:
            current[tag] = value
            continue
        if tag in header_tags:
            header[tag] = value
            continue
        # Attributes after header UUID but before class keys
        if current is None:
            header[tag] = value
        else:
            current[tag] = value

    if current is not None:
        class_keys.append(current)

    return {"header": header, "class_keys": class_keys}


def _b2hex(b: Optional[bytes]) -> str:
    if not b:
        return ""
    return b.hex()


def _u32(b: Optional[bytes]) -> Optional[int]:
    if not b:
        return None
    if len(b) >= 4:
        return struct.unpack(">I", b[-4:])[0]
    return int.from_bytes(b, "big")


def build_itunes_hash_line(header: Dict[str, bytes], wpky: bytes) -> Tuple[str, str, int]:
    """
    Returns (hash_line, generation_label, suggested_hashcat_mode).
    """
    salt = header.get("SALT", b"")
    iter_b = header.get("ITER", b"")
    dpic_b = header.get("DPIC", b"")
    dpsl = header.get("DPSL", b"")
    iterations = _u32(iter_b) or 0
    dpic = _u32(dpic_b)

    wpky_h = _b2hex(wpky)
    salt_h = _b2hex(salt)
    dpsl_h = _b2hex(dpsl)

    if dpsl and dpic is not None:
        # iOS 10+ style double-KDF parameters present
        line = f"$itunes_backup$*10*{wpky_h}*{iterations}*{salt_h}*{dpic}*{dpsl_h}"
        return line, "ios10_plus", 14800

    line = f"$itunes_backup$*9*{wpky_h}*{iterations}*{salt_h}**"
    return line, "ios_pre10", 14700


def extract_ios_backup_hash(backup_root: Path, out_dir: Path) -> Dict[str, Any]:
    """
    Locate Manifest.plist, parse BackupKeyBag, write:
      work/ios_backup.hash          — hashcat line
      work/ios_backup_hash_meta.json
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {
        "ok": False,
        "extractor": "ios_backup_hash",
        "artifacts": [],
        "message": "",
        "encrypted": None,
    }

    root = Path(backup_root)
    manifest = None
    for name in ("Manifest.plist", "manifest.plist"):
        candidate = root / name
        if candidate.is_file():
            manifest = candidate
            break
    if manifest is None:
        hits = list(root.glob("**/Manifest.plist"))[:3]
        manifest = hits[0] if hits else None
    if manifest is None:
        result["message"] = "No Manifest.plist found under backup root."
        return result

    try:
        with manifest.open("rb") as f:
            plist = plistlib.load(f)
    except Exception as e:
        result["message"] = f"Failed to parse Manifest.plist: {e}"
        return result

    # IsEncrypted may be bool; BackupKeyBag present implies encrypted
    is_encrypted = bool(plist.get("IsEncrypted") or plist.get("BackupKeyBag"))
    result["encrypted"] = is_encrypted
    if not is_encrypted:
        result["message"] = (
            "Backup does not appear encrypted (no BackupKeyBag / IsEncrypted). "
            "No password hash to extract — parse with iDriller instead."
        )
        result["ok"] = True  # not an error; nothing to recover
        return result

    keybag = plist.get("BackupKeyBag")
    if not isinstance(keybag, (bytes, bytearray)):
        result["message"] = "BackupKeyBag missing or not binary data."
        return result

    entries = _parse_keybag_tlv(bytes(keybag))
    if not entries:
        result["message"] = "BackupKeyBag TLV parse produced no entries."
        return result

    grouped = _group_keybag(entries)
    header = grouped["header"]
    class_keys = grouped["class_keys"]

    # Prefer a WPKY from a class-key block; fall back to any WPKY in header
    wpky = None
    for ck in class_keys:
        if "WPKY" in ck:
            wpky = ck["WPKY"]
            break
    if wpky is None:
        wpky = header.get("WPKY")
    if not wpky:
        # Last resort: first WPKY tag in raw entries
        for tag, val in entries:
            if tag == "WPKY":
                wpky = val
                break
    if not wpky:
        result["message"] = "No WPKY found in BackupKeyBag — cannot build verifier hash."
        return result

    if "SALT" not in header or "ITER" not in header:
        result["message"] = "Keybag header missing SALT/ITER — cannot build verifier hash."
        return result

    hash_line, generation, mode = build_itunes_hash_line(header, wpky)
    hash_path = out_dir / "ios_backup.hash"
    hash_path.write_text(hash_line + "\n", encoding="utf-8")

    meta = {
        "source_manifest": str(manifest),
        "generation": generation,
        "suggested_hashcat_mode": mode,
        "iterations": _u32(header.get("ITER")),
        "dpic": _u32(header.get("DPIC")),
        "has_dpsl": "DPSL" in header,
        "salt_hex": _b2hex(header.get("SALT")),
        "dpsl_hex": _b2hex(header.get("DPSL")),
        "wpky_len": len(wpky),
        "class_key_blocks": len(class_keys),
        "hash_line_prefix": hash_line[:32] + "…",
        "notes": [
            "This is a password verifier for the *backup password*, not the device passcode.",
            f"Suggested hashcat mode {mode} must be confirmed against your hashcat version.",
            "Real recovery requires LOCKBREAKER_ENABLE_REAL_BACKENDS=1 and lawful authority.",
        ],
    }
    meta_path = out_dir / "ios_backup_hash_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    result["ok"] = True
    result["message"] = (
        f"Extracted iOS backup password verifier ({generation}). "
        f"Suggested hashcat mode {mode}."
    )
    result["generation"] = generation
    result["suggested_hashcat_mode"] = mode
    result["artifacts"] = [
        {
            "path": str(hash_path),
            "sha256": hashlib.sha256(hash_path.read_bytes()).hexdigest(),
            "kind": "ios_backup_hash",
            "hashcat_mode": mode,
        },
        {
            "path": str(meta_path),
            "sha256": hashlib.sha256(meta_path.read_bytes()).hexdigest(),
            "kind": "ios_backup_hash_meta",
        },
    ]
    return result
