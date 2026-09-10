"""
Sundial — Database Schema
LoKi Timeline Reader

Design decisions baked into this schema:
- schema_version in a meta table (fix: spec had no versioning)
- inferred events live in a SEPARATE table from observed events, so a query
  physically cannot mix inference into observed-only data. Observed-only is
  the structural default.
- conflicts and links are indexed by event_id (fix: spec had no indexes)
- straight quotes only (fix: spec had a smart-quote that broke JSON)
"""
from __future__ import annotations

SCHEMA_VERSION = "3"

# ── Observed events: the court-grade spine ───────────────────────────────────
SCHEMA_EVENTS = """
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  event_id          TEXT PRIMARY KEY,
  category          TEXT,
  timestamp_start   TEXT NOT NULL,
  timestamp_end     TEXT,
  timestamp_quality TEXT,          -- EXACT | APPROXIMATE | RANGE | UNKNOWN
  timezone_basis    TEXT,          -- DEVICE | UTC | LOCAL
  summary_plain     TEXT,
  summary_technical TEXT,
  observability     TEXT,          -- always OBSERVED in this table
  confidence        REAL,
  source_count      INTEGER,
  -- Phase 3 correlation columns (created up-front so no fragile ALTER needed)
  entity_keys       TEXT,          -- JSON array of stable identity keys
  thread_key        TEXT,          -- conversation / thread id
  file_hash         TEXT,          -- if the event concerns a file
  location_cluster  TEXT           -- if pre-clustered
);

CREATE INDEX IF NOT EXISTS idx_events_start    ON events(timestamp_start);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_thread   ON events(thread_key);
CREATE INDEX IF NOT EXISTS idx_events_obs      ON events(observability);
"""

# ── Provenance: every event traces back to its source artifact ───────────────
SCHEMA_SOURCES = """
CREATE TABLE IF NOT EXISTS event_sources (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id       TEXT NOT NULL,
  source_path    TEXT,
  source_type    TEXT,            -- db | file | log | plist | cloud_export
  table_name     TEXT,
  record_id      TEXT,
  offset         INTEGER,
  parser_name    TEXT,
  parser_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_event ON event_sources(event_id);
"""

SCHEMA_HASH_REFS = """
CREATE TABLE IF NOT EXISTS event_hash_refs (
  event_id   TEXT NOT NULL,
  hash_type  TEXT,
  hash_value TEXT
);

CREATE INDEX IF NOT EXISTS idx_hashrefs_event ON event_hash_refs(event_id);
"""

# ── Conflicts: when two sources disagree, both values are preserved ──────────
SCHEMA_CONFLICTS = """
CREATE TABLE IF NOT EXISTS event_conflicts (
  conflict_id  TEXT PRIMARY KEY,
  event_id     TEXT NOT NULL,
  conflict_type TEXT,            -- TIMESTAMP | FIELD_MISMATCH | DUPLICATE_KEYS
  field_name   TEXT,
  a_value      TEXT,
  b_value      TEXT,
  a_source_id  INTEGER,
  b_source_id  INTEGER,
  severity     TEXT,             -- LOW | MEDIUM | HIGH
  note_plain   TEXT
);

CREATE INDEX IF NOT EXISTS idx_conflicts_event ON event_conflicts(event_id);
"""

# ── Links: relationships between events ──────────────────────────────────────
SCHEMA_LINKS = """
CREATE TABLE IF NOT EXISTS event_links (
  link_id     TEXT PRIMARY KEY,
  event_id_a  TEXT NOT NULL,
  event_id_b  TEXT NOT NULL,
  link_type   TEXT,             -- SAME_THREAD | SAME_ENTITY | SAME_HASH | SAME_SESSION
  link_reason TEXT,
  confidence  REAL
);

CREATE INDEX IF NOT EXISTS idx_links_a ON event_links(event_id_a);
CREATE INDEX IF NOT EXISTS idx_links_b ON event_links(event_id_b);
"""

# ── Gaps: absence as a first-class citizen ───────────────────────────────────
SCHEMA_GAPS = """
CREATE TABLE IF NOT EXISTS timeline_gaps (
  gap_id           TEXT PRIMARY KEY,
  gap_start        TEXT NOT NULL,
  gap_end          TEXT NOT NULL,
  duration_minutes INTEGER,
  gap_explained    INTEGER DEFAULT 0,   -- 0 = unexplained, 1 = explained
  explanations     TEXT                 -- JSON array
);

CREATE INDEX IF NOT EXISTS idx_gaps_start ON timeline_gaps(gap_start);
"""

# ── Inferred events: SEPARATE TABLE. Observed-only is the structural default. ─
SCHEMA_INFERRED = """
CREATE TABLE IF NOT EXISTS inferred_events (
  event_id             TEXT PRIMARY KEY,
  inference_type       TEXT,           -- e.g. LIKELY_APP_INTERACTION
  timestamp_estimated  TEXT,
  timestamp_range_start TEXT,
  timestamp_range_end   TEXT,
  summary_plain        TEXT,
  confidence           REAL,
  confidence_level     TEXT,           -- LOW | MEDIUM | HIGH
  confidence_reasons   TEXT,           -- JSON array of plain-language reasons
  supporting_event_ids TEXT,           -- JSON array of observed event_ids
  hidden               INTEGER DEFAULT 0  -- investigator can hide individual inferences
);

CREATE INDEX IF NOT EXISTS idx_inferred_ts ON inferred_events(timestamp_estimated);
"""

ALL_SCHEMA = [
    SCHEMA_EVENTS,
    SCHEMA_SOURCES,
    SCHEMA_HASH_REFS,
    SCHEMA_CONFLICTS,
    SCHEMA_LINKS,
    SCHEMA_GAPS,
    SCHEMA_INFERRED,
]
