# Read-Only Evidence SQLite Fix Log

**Date:** 2026-08-15  
**Doctrine:** Source evidence is never opened read-write. No WAL/journal/SHM files may be created beside evidence.

## Shared helper

- `_shared/loki_sqlite.py` — `open_evidence_ro()` and `open_working_rw()`

## Files patched (source evidence opens → mode=ro + query_only)

| File | Change |
|------|--------|
| `myrecord/preservation/engine.py` | AddressBook / sms.db / call_history → RO helper |
| `idriller/idriller.py` | ManifestDB.open → RO URI |
| `integrity_breaker/platform_analyzers.py` | Manifest.db sanity check → RO URI |
| `lockbreaker_complete/worker/extractors/ios_keychain_and_android_pattern.py` | locksettings.db → RO URI |
| `lockbreaker/worker/extractors/ios_keychain_and_android_pattern.py` | same |
| `bardo/bardo_adapters/loki_modules/loki_adapter.py` | evidence_db_path + case_db_path ingest → RO URI |
| `update_trap/update_trap/core/sqlite_schema.py` | Removed RW fallback; RO failure is hard error |

## Already correct (left as-is)

- `truthrelicquery/truthrelicquery.py` — already `mode=ro`
- `memory_snare/sqlite_reader.py` — already `open_readonly` / consistent copy pattern
- `sundial/sundial/core/bundle.py` — case DB opened RO for reading
- `update_trap` primary path was already RO

## Intentionally read-write (LoKi-owned working DBs)

- `bardo/bardo_artifact_store/storage_sqlite.py` — our artifact store
- `chronochain/timeline_store.py` — our timeline DB
- `pattern_harvester/storage/findings_db.py` — our findings store
- `nimbus_bridge/.../loki/writer.py` — our normalized Loki DB
- `nimbus_bridge/.../analysis/*` — analysis against *our* Loki DB
- `sorcerers_stone_v2/.../storage.py` — our store
- `sundial` demo / `init_empty_db` — creates our schema

## Policy going forward

Any new code that opens a path under an evidence root, backup, or image must use `open_evidence_ro` (or equivalent URI `mode=ro`). RW is reserved for databases the platform creates under a case workspace.
