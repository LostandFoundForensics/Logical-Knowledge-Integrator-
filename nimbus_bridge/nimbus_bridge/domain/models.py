"""
nimbus_bridge/domain/models.py

Final domain models spanning all four providers.

BUG FIXED: AppleScope previously subclassed MetaScope directly
(`class AppleScope(MetaScope)`), which meant every AppleScope instance
silently carried facebook_enabled/instagram_enabled/messages_enabled/
max_messages_per_thread/etc — fields that have no meaning for an
Apple iCloud import and that nothing validated against. Each provider
now has its own scope class inheriting from a shared ScopeBase that
only carries fields genuinely common to every provider (import_id,
provider). Provider-specific toggles live only on that provider's own
scope class.

ADDED: MicrosoftScope didn't exist anywhere in any paste, despite
microsoft/parse_runner.py's run_microsoft_phase6 needing a scope-like
set of toggles analogous to every other provider. Added here.

RecognitionDataset.dataset is typed as `str` (not the Dataset enum)
because google_takeout's RecognitionDataset originally used the actual
Dataset enum, while meta_dyi's used a plain str ("messages", "contacts",
which don't even match Dataset enum values like "meta_messages").
Kept as `str` to avoid forcing meta_dyi's recognizer to silently break.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict
from datetime import datetime
from .enums import Provider, AcquiredMethod, ObservedOrInferred, Confidence, Dataset


class CaseRef(BaseModel):
    case_id: str
    case_name: str
    examiner: str


class ImportRef(BaseModel):
    import_id: str
    source_label: str
    vault_root: str
    acquired_method: AcquiredMethod = AcquiredMethod.USER_EXPORT


class RecognitionDataset(BaseModel):
    dataset: str
    present: bool
    paths: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ProviderRecognition(BaseModel):
    provider: Provider
    import_id: str
    recognized: bool
    takeout_root: Optional[str] = None
    datasets: List[RecognitionDataset] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MetaRecognition(ProviderRecognition):
    platforms: List[str] = Field(default_factory=list)


# ── Scope base + one real class per provider (FIX: no cross-provider inheritance) ──

class ScopeBase(BaseModel):
    import_id: str
    provider: Provider


class TakeoutScope(ScopeBase):
    provider: Provider = Provider.GOOGLE_TAKEOUT

    gmail_enabled: bool = False
    contacts_enabled: bool = False
    calendar_enabled: bool = False
    location_enabled: bool = False
    drive_meta_enabled: bool = False

    gmail_index_only: bool = False
    gmail_extract_attachments: bool = False
    location_normalize_tz: bool = False


class MetaScope(ScopeBase):
    provider: Provider = Provider.META_DYI

    facebook_enabled: bool = True
    instagram_enabled: bool = True

    messages_enabled: bool = False
    contacts_enabled: bool = False
    security_enabled: bool = False
    media_linking_enabled: bool = False

    extract_media_blobs: bool = False
    max_messages_per_thread: Optional[int] = None
    allow_epoch_to_utc: bool = True


class AppleScope(ScopeBase):
    provider: Provider = Provider.APPLE_ICLOUD

    photos_enabled: bool = False
    drive_enabled: bool = False
    contacts_enabled: bool = False
    calendar_enabled: bool = False
    notes_enabled: bool = False


class MicrosoftScope(ScopeBase):
    """Not present in any prior paste — added so run_microsoft_phase6
    has a real scope object analogous to every other provider."""
    provider: Provider = Provider.MICROSOFT

    mail_enabled: bool = False
    onedrive_enabled: bool = False
    contacts_enabled: bool = False
    calendar_enabled: bool = False
    security_enabled: bool = False


# ── Shared result models ──────────────────────────────────────────────────────

class SourceProvenance(BaseModel):
    """
    Documentation/validation model only. The FINAL LokiWriter signature
    used across all four providers' parsers is the flat-kwarg form
    (see services/loki/writer.py), not this object — but the 7-field
    grouping it names is referenced often enough in tests/reports that
    it's kept as a named, importable shape.
    """
    source_provider: Provider
    source_dataset: Dataset
    source_path: str
    source_sha256: str
    source_record_locator: Dict[str, Any] = Field(default_factory=dict)
    acquired_method: AcquiredMethod = AcquiredMethod.USER_EXPORT
    observed_or_inferred: ObservedOrInferred = ObservedOrInferred.OBSERVED
    confidence: Confidence = Confidence.MED


class MappingRecord(BaseModel):
    input_field: str
    mapped_to: str
    transformation: Optional[str] = None
    loss: Optional[str] = "none"


class LokiWriteStats(BaseModel):
    messages_written: int = 0
    contacts_written: int = 0
    events_written: int = 0
    locations_written: int = 0
    files_written: int = 0
    warnings: List[str] = Field(default_factory=list)


class ParseRunResult(BaseModel):
    import_id: str
    provider: Provider
    scope: Optional[ScopeBase] = None
    started_utc: datetime
    completed_utc: datetime
    stats: LokiWriteStats
    gaps: List[str] = Field(default_factory=list)
    reports: Dict[str, str] = Field(default_factory=dict)
