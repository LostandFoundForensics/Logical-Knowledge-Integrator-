"""Workbench stations — recommended tool groups for operators."""
from __future__ import annotations

from typing import Dict, List


STATIONS: List[Dict[str, object]] = [
    {
        "id": "intake",
        "label": "Intake",
        "description": "Identify backup/export type and readiness.",
        "tools": ["echoreader", "nimbus_bridge"],
    },
    {
        "id": "access",
        "label": "Access",
        "description": "Lawful access surface and hash extraction.",
        "tools": ["lockbreaker", "diamond_forger"],
    },
    {
        "id": "android",
        "label": "Android",
        "description": "Folder-dump acquisition parse.",
        "tools": ["android_excavator", "memory_snare"],
    },
    {
        "id": "ios",
        "label": "iOS",
        "description": "Backup parse depth.",
        "tools": ["idriller", "recall_engine"],
    },
    {
        "id": "bulk",
        "label": "Bulk & FS",
        "description": "Patterns, inventory, integrity indicators.",
        "tools": ["pattern_harvester", "truthrelic", "integrity_breaker"],
    },
    {
        "id": "case",
        "label": "Case & timeline",
        "description": "Aggregate, fuse, read, draft.",
        "tools": ["bardo", "chronochain", "sundial", "witness_light"],
    },
    {
        "id": "qa",
        "label": "Validation",
        "description": "Synthetic data and drift checks.",
        "tools": ["truthloom", "update_trap"],
    },
]


def list_stations() -> List[Dict[str, object]]:
    return list(STATIONS)
