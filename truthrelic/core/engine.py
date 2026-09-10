from __future__ import annotations

from typing import Dict, List


def list_actions() -> List[Dict[str, str]]:
    return [
        {
            "id": "inventory",
            "label": "Folder inventory",
            "description": "List files under a folder with sizes and times (optional SHA-256).",
        },
        {
            "id": "probe",
            "label": "Disk image probe",
            "description": "Read MBR/GPT map and filesystem signature hints (no mount).",
        },
        {
            "id": "hash",
            "label": "Hash a file",
            "description": "SHA-256 of a single evidence file (read-only).",
        },
    ]
