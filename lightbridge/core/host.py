"""Locate libimobiledevice-style host binaries."""
from __future__ import annotations

import shutil
from typing import Optional

from lightbridge.core.models import HostTools

TOOL_NAMES = {
    "idevice_id": "idevice_id",
    "ideviceinfo": "ideviceinfo",
    "idevicepair": "idevicepair",
    "idevicebackup2": "idevicebackup2",
    "ideviceinstaller": "ideviceinstaller",
}


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def probe_host_tools() -> HostTools:
    t = HostTools()
    t.idevice_id = which("idevice_id")
    t.ideviceinfo = which("ideviceinfo")
    t.idevicepair = which("idevicepair")
    t.idevicebackup2 = which("idevicebackup2")
    t.ideviceinstaller = which("ideviceinstaller")
    if not t.any_available:
        t.notes.append(
            "No libimobiledevice tools on PATH. "
            "Install idevice* packages or work offline from a Finder/iTunes backup."
        )
    else:
        t.notes.append("Host tools detected — device list may work over USB.")
    return t
