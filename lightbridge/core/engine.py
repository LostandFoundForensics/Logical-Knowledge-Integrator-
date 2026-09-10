"""LightBridge engine — probe, list, info (subprocess to host tools only)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from lightbridge.core.host import probe_host_tools as _probe
from lightbridge.core.models import DeviceRef, HostTools


def probe_host_tools() -> HostTools:
    return _probe()


def list_actions() -> List[Dict[str, str]]:
    return [
        {
            "id": "tools",
            "label": "Host tools",
            "description": "Check for idevice_id / ideviceinfo / idevicebackup2.",
        },
        {
            "id": "devices",
            "label": "List devices",
            "description": "UDID list from idevice_id --list (if available).",
        },
        {
            "id": "info",
            "label": "Device info",
            "description": "ideviceinfo for one UDID (if available).",
        },
        {
            "id": "guide",
            "label": "Backup guidance",
            "description": "How to produce a backup folder for iDriller / EchoReader.",
        },
    ]


def _run(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def list_devices() -> List[DeviceRef]:
    tools = _probe()
    if not tools.idevice_id:
        return []
    try:
        proc = _run([tools.idevice_id, "-l"])
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    devices: List[DeviceRef] = []
    for line in (proc.stdout or "").splitlines():
        udid = line.strip()
        if udid:
            devices.append(DeviceRef(udid=udid))
    return devices


def device_info(udid: str) -> Optional[DeviceRef]:
    tools = _probe()
    if not tools.ideviceinfo:
        return None
    try:
        proc = _run([tools.ideviceinfo, "-u", udid])
    except Exception:
        return None
    if proc.returncode != 0:
        return DeviceRef(udid=udid, raw={"error": (proc.stderr or "")[:300]})
    raw: Dict[str, str] = {}
    for line in (proc.stdout or "").splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            raw[k.strip()] = v.strip()
    return DeviceRef(
        udid=udid,
        name=raw.get("DeviceName") or raw.get("Device Name") or "",
        product_type=raw.get("ProductType") or "",
        product_version=raw.get("ProductVersion") or "",
        raw=raw,
    )


def backup_guidance() -> List[str]:
    return [
        "Preferred offline path: obtain a standard Finder/iTunes backup folder "
        "(contains Manifest.db) under lawful authority.",
        "Then: python -m echoreader inspect <backup_dir>",
        "Unencrypted: python -m idriller extract <backup_dir> --out ./out",
        "Depth: python -m recall_engine scan <backup_dir> --out ./out",
        "Encrypted: LockBreaker ios_backup_hash (dry-run) → Diamond Forger if authorized.",
        "Live USB backup via idevicebackup2 is optional and host-dependent; "
        "LightBridge will not invoke it unless you explicitly request backup with authority.",
    ]


def request_backup(
    udid: str,
    dest: Path,
    *,
    examiner: str,
    authority: str,
    execute: bool = False,
) -> Dict[str, object]:
    """
    Optional live backup via idevicebackup2.
    Default execute=False → dry-run only.
    """
    tools = _probe()
    result: Dict[str, object] = {
        "udid": udid,
        "dest": str(dest),
        "execute": execute,
        "examiner": examiner,
        "authority": authority,
    }
    if len((examiner or "").strip()) < 2 or len((authority or "").strip()) < 4:
        result["ok"] = False
        result["message"] = "Examiner and authority required."
        return result
    if not tools.idevicebackup2:
        result["ok"] = False
        result["message"] = "idevicebackup2 not on PATH."
        result["guidance"] = backup_guidance()
        return result
    if not execute:
        result["ok"] = True
        result["message"] = "Dry-run: would run idevicebackup2 backup --full."
        result["cmd"] = [tools.idevicebackup2, "backup", "--full", str(dest)]
        return result
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        proc = _run(
            [tools.idevicebackup2, "-u", udid, "backup", "--full", str(dest)],
            timeout=3600,
        )
        result["ok"] = proc.returncode == 0
        result["returncode"] = proc.returncode
        result["stdout_tail"] = (proc.stdout or "")[-1500:]
        result["stderr_tail"] = (proc.stderr or "")[-1500:]
        result["message"] = "Backup finished" if result["ok"] else "Backup failed"
    except Exception as e:
        result["ok"] = False
        result["message"] = str(e)
    return result
