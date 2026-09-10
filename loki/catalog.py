"""Catalog of operational LoKi tools (rebuilt CLI path)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ToolEntry:
    tool_id: str
    label: str
    module: str  # python -m MODULE
    role: str
    pythonpath_hint: str  # "" = loki_complete root


TOOLS: List[ToolEntry] = [
    ToolEntry("lockbreaker", "LockBreaker", "lockbreaker", "Access / lock & backup hash", ""),
    ToolEntry("echoreader", "EchoReader", "echoreader", "Backup intake / readiness", ""),
    ToolEntry("diamond_forger", "Diamond Forger", "diamond_forger", "Authorized hash recovery", ""),
    ToolEntry("android_excavator", "Android Excavator", "android_excavator", "Android SMS/calls/contacts", ""),
    ToolEntry("memory_snare", "Memory Snare", "memory_snare", "Android accounts/browser/wifi", ""),
    ToolEntry("idriller", "iDriller", "idriller", "iOS backup SMS/calls/contacts", ""),
    ToolEntry("recall_engine", "Recall Engine", "recall_engine", "iOS notes/Safari/calendar", ""),
    ToolEntry("pattern_harvester", "Pattern Harvester", "pattern_harvester", "Emails/phones/URLs/IPs", ""),
    ToolEntry("truthrelic", "Truth Relic", "truthrelic", "Folder inventory / image probe", ""),
    ToolEntry("integrity_breaker", "Integrity Breaker", "integrity_breaker", "IOC indicators", ""),
    ToolEntry("update_trap", "Update Trap", "update_trap", "Snapshot + schema drift", "update_trap"),
    ToolEntry("nimbus_bridge", "Nimbus Bridge", "nimbus_bridge", "Google Takeout intake", "nimbus_bridge"),
    ToolEntry("bardo", "Bardo Engine", "bardo", "Case store / timeline", ""),
    ToolEntry("chronochain", "ChronoChain", "chronochain", "Timeline fusion", ""),
    ToolEntry("ghostframe", "Ghostframe", "ghostframe", "Memory analysis surface", ""),
    ToolEntry("sundial", "Sundial", "sundial", "Human timeline view", "sundial"),
    ToolEntry("witness_light", "Witness Light", "witness_light", "Draft observation report", ""),
    ToolEntry("truthloom", "Truthloom", "truthloom", "Synthetic validation data", "truthloom"),
    ToolEntry("chopshop", "Chop Shop", "chopshop", "Workbench / environment probe", ""),
    ToolEntry("lightbridge", "LightBridge", "lightbridge", "iOS USB / host tools bridge", ""),
]


def list_tools() -> List[ToolEntry]:
    return list(TOOLS)
