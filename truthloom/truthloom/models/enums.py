from enum import Enum

class TruthState(str, Enum):
    DRAFT_TRUTH = "draft_truth"
    OBSERVED_TRUTH = "observed_truth"

class Confidence(str, Enum):
    CERTAIN = "certain"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"

class ArtifactType(str, Enum):
    MESSAGE = "message"
    CALL = "call"
    PHOTO_VIDEO = "photo_video"
    APP_INSTALL = "app_install"
    NOTIFICATION = "notification"
    LOCATION_EVENT = "location_event"
    WEB_VISIT = "web_visit"
    CUSTOM = "custom"

class DatasetMode(str, Enum):
    NORMAL = "normal"
    QUARANTINE = "quarantine"

class SourceType(str, Enum):
    GENERIC_FILES = "generic_files"
    IOS_BACKUP_FOLDER = "ios_backup_folder"
    ANDROID_PULL_FOLDER = "android_pull_folder"
    ANDROID_BACKUP_FOLDER = "android_backup_folder"
    TOOL_EXPORT_REFERENCE = "tool_export_reference"

class IntakeState(str, Enum):
    STAGED = "staged"
    COPIED = "copied"
    HASHED = "hashed"
    EXCLUDED = "excluded"
    MISSING = "missing"
    HASH_MISMATCH = "hash_mismatch"

class CopyPolicy(str, Enum):
    COPY_ONLY = "copy_only"
    COPY_AND_FLATTEN = "copy_and_flatten"
    COPY_PRESERVE_TREE = "copy_preserve_tree"

class SourceMethod(str, Enum):
    MANUAL_ENTRY = "manual_entry"
    IMPORT_CSV = "import_csv"
    IMPORT_JSON = "import_json"
    IMPORT_TOOL_EXPORT = "import_tool_export"
