"""
LightBridge — iOS device communication surface (libimobiledevice-class role).

Discovers host tools (idevice_id, ideviceinfo, idevicebackup2, …), lists
attached devices when tools exist, and records pairing/backup readiness.

Does not implement usbmuxd itself. Prefer offline backups → EchoReader / iDriller
when USB is unavailable. Never pairs or backs up without explicit operator intent.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["probe_host_tools", "list_devices", "device_info", "list_actions"]

from lightbridge.core.engine import probe_host_tools, list_devices, device_info, list_actions
