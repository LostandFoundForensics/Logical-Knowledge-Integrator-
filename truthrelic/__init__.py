"""
Truth Relic — filesystem and image surface inspection (read-only).

- Folder trees: inventory, hashes, timestamps
- Disk images: MBR/GPT partition map + filesystem signature hints
Never mounts or modifies evidence.

Sleuth Kit–class *surface* tool for LoKi — not a full FS driver suite.
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["inventory_tree", "probe_image", "list_actions"]

from truthrelic.core.inventory import inventory_tree
from truthrelic.probe.image import probe_image
from truthrelic.core.engine import list_actions
