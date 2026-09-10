"""
Update Trap — core/config.py
Package-level configuration constants.
"""
from __future__ import annotations

DEFAULT_SOURCE_PROFILES = [
    "android_extraction",
    "ios_backup",
    "mounted_image",
    "generic_folder",
]

DEFAULT_TARGETS = ["accounts", "comms", "web", "media", "system", "apps"]

DEFAULT_STRUCTURED_KINDS = ["json", "plist", "xml"]

PROFILE_DISPLAY_NAMES = {
    "android_extraction": "Android Extraction",
    "ios_backup": "iOS Backup",
    "mounted_image": "Mounted Image",
    "generic_folder": "Generic Folder",
}
