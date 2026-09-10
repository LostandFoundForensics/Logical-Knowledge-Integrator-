"""
Read-only disk image probe: size, MBR/GPT partition map, FS signature hints.

Does not mount. Does not modify. Bounded reads only.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Optional, Tuple

from truthrelic.core.models import ImageProbe, PartitionInfo

GPT_SIGNATURE = b"EFI PART"
# Common partition type GUIDs (subset)
GPT_TYPE_HINTS = {
    "00000000-0000-0000-0000-000000000000": "unused",
    "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7": "microsoft_basic_data",
    "c12a7328-f81f-11d2-ba4b-00a0c93ec93b": "efi_system",
    "0fc63daf-8483-4772-8e79-3d69d8477de4": "linux_filesystem",
    "48465300-0000-11aa-aa11-00306543ecac": "apple_hfs",
    "7c3457ef-0000-11aa-aa11-00306543ecac": "apple_apfs",
}


def _read(path: Path, offset: int, size: int) -> bytes:
    with path.open("rb") as f:
        f.seek(offset)
        return f.read(size)


def _u32(b: bytes, off: int = 0) -> int:
    return struct.unpack_from("<I", b, off)[0]


def _u16(b: bytes, off: int = 0) -> int:
    return struct.unpack_from("<H", b, off)[0]


def _guid_str(b: bytes) -> str:
    """Microsoft-style mixed-endian GUID to string."""
    if len(b) < 16:
        return "unknown"
    d1, d2, d3 = struct.unpack_from("<IHH", b, 0)
    d4 = b[8:10].hex()
    d5 = b[10:16].hex()
    return f"{d1:08x}-{d2:04x}-{d3:04x}-{d4}-{d5}"


def parse_mbr(path: Path) -> Tuple[str, List[PartitionInfo], List[str]]:
    notes: List[str] = []
    sector = _read(path, 0, 512)
    if len(sector) < 512:
        return "unknown", [], ["Image smaller than 512 bytes"]
    if sector[510:512] != b"\x55\xaa":
        notes.append("No MBR 0x55AA signature")
        return "none", [], notes

    parts: List[PartitionInfo] = []
    # protective GPT?
    for i in range(4):
        off = 446 + i * 16
        entry = sector[off : off + 16]
        ptype = entry[4]
        start = _u32(entry, 8)
        size = _u32(entry, 12)
        if ptype == 0 or size == 0:
            continue
        hint = {
            0x07: "ntfs_or_exfat_like",
            0x0B: "fat32",
            0x0C: "fat32_lba",
            0x83: "linux",
            0xEE: "gpt_protective",
            0xAF: "hfs_like",
        }.get(ptype, f"type_0x{ptype:02x}")
        parts.append(
            PartitionInfo(index=i, start_lba=start, size_lba=size, type_hint=hint)
        )
    if any(p.type_hint == "gpt_protective" for p in parts):
        notes.append("Protective MBR suggests GPT")
        return "mbr_protective", parts, notes
    if parts:
        return "mbr", parts, notes
    return "mbr", parts, notes + ["MBR signature present but no active partition entries"]


def parse_gpt(path: Path, *, block_size: int = 512) -> Tuple[str, List[PartitionInfo], List[str]]:
    notes: List[str] = []
    # Primary GPT header at LBA 1
    hdr = _read(path, block_size, block_size)
    if len(hdr) < 92 or hdr[0:8] != GPT_SIGNATURE:
        return "none", [], ["No GPT header at LBA 1"]

    # header fields (UEFI)
    # 0x48: partition entry LBA (8 bytes LE)
    # 0x50: number of entries (4)
    # 0x54: size of entry (4)
    part_lba = struct.unpack_from("<Q", hdr, 0x48)[0]
    num_entries = _u32(hdr, 0x50)
    entry_size = _u32(hdr, 0x54)
    if entry_size < 128 or num_entries > 256:
        notes.append(f"Unusual GPT entry table (n={num_entries}, size={entry_size})")
        num_entries = min(num_entries, 128)
        entry_size = max(entry_size, 128)

    table_off = part_lba * block_size
    table = _read(path, table_off, num_entries * entry_size)
    parts: List[PartitionInfo] = []
    for i in range(num_entries):
        e = table[i * entry_size : (i + 1) * entry_size]
        if len(e) < 128:
            break
        type_guid = _guid_str(e[0:16])
        if type_guid == "00000000-0000-0000-0000-000000000000":
            continue
        first_lba = struct.unpack_from("<Q", e, 32)[0]
        last_lba = struct.unpack_from("<Q", e, 40)[0]
        name_raw = e[56:128].decode("utf-16-le", errors="ignore").rstrip("\x00")
        hint = GPT_TYPE_HINTS.get(type_guid, type_guid)
        parts.append(
            PartitionInfo(
                index=i,
                start_lba=first_lba,
                size_lba=max(0, last_lba - first_lba + 1),
                type_hint=hint,
                name=name_raw,
            )
        )
    return "gpt", parts, notes


def fs_signature_hints(path: Path, partitions: List[PartitionInfo], block_size: int) -> List[str]:
    hints: List[str] = []
    # Check start of image and each partition start
    offsets = [0] + [p.start_lba * block_size for p in partitions[:8]]
    for off in offsets:
        try:
            buf = _read(path, off, 4096)
        except OSError:
            continue
        if len(buf) < 1024:
            continue
        # ext superblock at +1024
        if len(buf) >= 1080:
            magic = struct.unpack_from("<H", buf, 1024 + 0x38)[0]
            if magic == 0xEF53:
                hints.append(f"ext_superblock@+{off}+1024")
        if buf[0:8] == b"NTFS    ":
            hints.append(f"ntfs@+{off}")
        if buf[0:4] == b"hsqs":
            hints.append(f"squashfs@+{off}")
        if buf[0:3] == b"XFSB":
            hints.append(f"xfs@+{off}")
        # APFS container NXPB
        if buf[32:36] == b"NXSB":
            hints.append(f"apfs_nxsb@+{off}")
        # HFS+ 
        if len(buf) >= 1024 + 2 and buf[1024:1026] == b"H+":
            hints.append(f"hfs_plus@+{off}+1024")
    # dedupe preserve order
    seen = set()
    out = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def probe_image(path: str | Path) -> ImageProbe:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Not a file (need disk image path): {path}")
    size = path.stat().st_size
    notes: List[str] = []
    block_size = 512

    scheme, parts, n1 = parse_mbr(path)
    notes.extend(n1)

    if scheme in ("mbr_protective", "none", "mbr") or not parts:
        gpt_scheme, gpt_parts, n2 = parse_gpt(path, block_size=block_size)
        notes.extend(n2)
        if gpt_scheme == "gpt" and gpt_parts:
            scheme = "gpt"
            parts = gpt_parts

    if scheme == "mbr_protective" and not any(p.type_hint != "gpt_protective" for p in parts):
        # try GPT as authoritative
        gpt_scheme, gpt_parts, n3 = parse_gpt(path, block_size=block_size)
        notes.extend(n3)
        if gpt_parts:
            scheme = "gpt"
            parts = gpt_parts

    hints = fs_signature_hints(path, parts, block_size)
    return ImageProbe(
        path=str(path),
        size_bytes=size,
        scheme=scheme,
        block_size=block_size,
        partitions=parts,
        fs_hints=hints,
        notes=notes,
    )
