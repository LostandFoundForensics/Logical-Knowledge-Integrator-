"""
nimbus_bridge/domain/enums.py

Final, complete enum set spanning all four providers (Google Takeout,
Meta DYI, Apple iCloud, Microsoft).

BUG FIXED: Provider.APPLE_ICLOUD and Provider.MICROSOFT were referenced
throughout every Apple/Microsoft parser module and recognizer
(recognize_apple_icloud, recognize_microsoft, every loki.write_*(prov=...)
call in icloud/* and microsoft/*) but neither was ever actually added
to any Provider enum across the whole paste sequence — every one of
those call sites would have raised AttributeError at runtime. Added
here.

BUG FIXED: Dataset.ICLOUD_CONTACTS, MICROSOFT_CONTACTS, MICROSOFT_CALENDAR,
and MICROSOFT_SECURITY were used in write_* calls (icloud/contacts.py,
microsoft/contacts.py, microsoft/calendar.py, microsoft/security.py)
but never defined in any Dataset enum paste. Added here.

ICLOUD_DRIVE and ICLOUD_NOTES are added preemptively since the package
tree lists drive.py and notes.py under apple_icloud/, even though
neither file's contents have been provided yet.
"""
from enum import Enum


class Provider(str, Enum):
    GOOGLE_TAKEOUT = "google_takeout"
    META_DYI = "meta_dyi"
    APPLE_ICLOUD = "apple_icloud"      # FIX: was missing
    MICROSOFT = "microsoft"            # FIX: was missing


class AcquiredMethod(str, Enum):
    USER_EXPORT = "user_export"
    OAUTH_EXPORT = "oauth_export"
    RECORD_ONLY = "record_only"


class ObservedOrInferred(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"


class Confidence(str, Enum):
    HIGH = "high"
    MED = "med"
    LOW = "low"


class Dataset(str, Enum):
    # Google
    MAIL = "mail"
    CONTACTS = "contacts"
    CALENDAR = "calendar"
    LOCATION_HISTORY = "location_history"
    DRIVE_META = "drive_metadata"

    # Meta
    META_MESSAGES = "meta_messages"
    META_CONTACTS = "meta_contacts"
    META_SECURITY = "meta_security"
    META_MEDIA = "meta_media"

    # Apple iCloud
    ICLOUD_PHOTOS = "icloud_photos"
    ICLOUD_CALENDAR = "icloud_calendar"
    ICLOUD_CONTACTS = "icloud_contacts"        # FIX: was missing
    ICLOUD_DRIVE = "icloud_drive"              # added ahead of drive.py
    ICLOUD_NOTES = "icloud_notes"              # added ahead of notes.py

    # Microsoft
    MICROSOFT_MAIL = "microsoft_mail"
    MICROSOFT_ONEDRIVE = "microsoft_onedrive"
    MICROSOFT_CONTACTS = "microsoft_contacts"   # FIX: was missing
    MICROSOFT_CALENDAR = "microsoft_calendar"   # FIX: was missing
    MICROSOFT_SECURITY = "microsoft_security"   # FIX: was missing
