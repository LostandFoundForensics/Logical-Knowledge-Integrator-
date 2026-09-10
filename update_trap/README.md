# Update Trap (LoKi)

## Quick CLI (Phase 1 — operational)

```bash
export PYTHONPATH=/path/to/loki_complete/update_trap

python -m update_trap snapshot /path/to/extract --label before --out ./snap_before.json
python -m update_trap snapshot /path/to/extract_after --label after --out ./snap_after.json
python -m update_trap diff ./snap_before.json ./snap_after.json --out ./diff_out
```

Hashes every file, records SQLite table/column maps (read-only), diffs presence and schema. Does **not** auto-patch parsers.

---


Update Trap is LoKi's OTA/app/OS schema-drift detector. Mobile forensics
parsers break silently when a device gets a software update — a file
moves, a column gets renamed, a database disappears. Update Trap takes a
snapshot before and after an update, diffs them, and produces a
court-defensible record of exactly what changed — then closes the loop
by flagging which LoKi parsers are now at risk and routing a suggested
fix through mandatory human review before it's ever applied.

Read-only by default. Every action is investigator-triggered and logged.
Truth over convenience: column renames and structured-key renames are
never guessed — only suggested as candidates for human confirmation.

## Three phases

```
Phase 1 — Snapshot + Diff
  Hash every file in a folder, introspect SQLite schemas read-only,
  diff two snapshots at the file and schema level, export a claim pack.

Phase 2 — Scoped Targeting + Structured Keys
  Instead of hashing everything, target specific packs (accounts, comms,
  web, media, system, apps) for a given source profile (Android
  extraction / iOS backup / mounted image / generic folder). Also diffs
  JSON/plist/XML key structure, not just SQLite schemas.

Phase 3 — Closed-Loop Parser Maintenance
  Cross-reference the diff against a parser dependency registry, flag
  at-risk parsers, generate a suggested config-only patch, route it
  through human review + approval, apply only the approved patch,
  re-validate against a known-good dataset (Truthloom), and surface
  everything on a readiness dashboard.
```

## Full lifecycle (Phase 3)

```
OS Update / OTA / App Change
        ↓
Update Trap detects change
        ↓
Parser risk assessed         (breakage.py — real glob matching)
        ↓
Suggested patch staged       (suggested_patch.py — scoped to the parser's own paths)
        ↓
Human review + approval      (patch_review.json → approved_patch.json)
        ↓
Config-only patch applied    (apply_patch.py — guarded against missing tables)
        ↓
Truthloom validation         (validation_event.json)
        ↓
Parser marked "Known-Good"
        ↓
Ready for next update
```

## Package layout

```
update_trap/
  README.md
  requirements.txt
  parsers/
    parser_registry.json       sample registry for the breakage detector
  signatures/
    android_signatures.json    sample advisory signature library
  runs/                        created automatically; stores case bundles

  update_trap/
    __init__.py
    app.py                     Tkinter UI — Phase 1+2+3 all wired in
    ui_bw.py                   black/white theme helper

    core/
      __init__.py
      config.py                 profile/target/structured-kind constants
      models.py                 Snapshot, SnapshotScope, StructuredKeySchema
      logbook.py                 court-style investigator action log
      hashing.py                 sha256_file
      sqlite_schema.py          read-only SQLite introspection (logged fallback)
      structured_schema.py      JSON/plist/XML key extraction        [Phase 2]
      targeting.py              source-profile target packs           [Phase 2]
      patterns.py               glob matching (allow_path/matches_any) [Phase 2]
      snapshot.py                SnapshotBuilder (scope-aware)
      diff_engine.py             DiffEngine (files + schema + structured keys)
      rules_engine.py            RulesEngine — never guesses renames
      export.py                  Exporter — claim pack packaging
      signatures.py              SignatureLibrary (advisory)          [Phase 3]
      breakage.py                ParserBreakageDetector (glob-matched) [Phase 3]
      suggested_patch.py         generate_suggested_patches (scoped)   [Phase 3]
      apply_patch.py             apply_approved_patch (KeyError-guarded) [Phase 3]
      dashboard.py                build_dashboard (readiness board)     [Phase 3]
      exhibits.py                 generate_exhibit_pack (4 court exhibits) [Phase 3]
      claim_pack_importer.py      ClaimPackImporter (LoKi ingestion)      [Phase 3]
```

## Fixes applied in this build

| # | Fix |
|---|-----|
| 1 | **Canonical `models.py` resolved.** Two incompatible drafts existed — one with `SnapshotScope`/`StructuredKeySchema`, one without. The version with scope is canonical, since `config.py`'s target packs and `structured_schema.py` both depend on it existing. |
| 2 | **`SnapshotBuilder` uses a direct `FileRecord` import** instead of the fragile `__import__("update_trap").core.models.FileRecord` pattern, and the dead `snap.files.get(rel) or FileRecord(...)` fallback (which always evaluated to the right-hand side anyway) is removed. |
| 3 | **`read_sqlite_schema`'s read-only fallback is now logged**, not silent. If the URI-mode read-only open fails for any reason, that's recorded in the LogBook before falling back to a standard connection — never a silent risk of an unrecorded write path to evidence. |
| 4 | **`claim_pack.json` uses ISO 8601 timestamps**, matching the convention used everywhere else in LoKi (LockBreaker, Witness Light), instead of a raw `time.time()` float. `event_id` and `scope` are now always written into the claim pack too, since `claim_pack_importer.py` and `dashboard.py` both expected to read them but the original `Exporter.export()` never wrote them. |
| 5 | **Duplicate `BreakageFinding`/`ParserBreakageDetector` resolved.** These were pasted twice as literal duplicates — same pattern seen earlier in Ghostframe, Integrity Breaker, and Open Record. `breakage.py` now has one definition. |
| 6 | **Real glob matching in the breakage detector.** The original `analyze()` did naive substring matching (`p.replace("**/", "") in cp`), which both over-matches (a glob fragment that happens to appear as a substring of an unrelated path) and under-matches (multi-wildcard globs don't degrade into a substring check). Now uses `matches_any()` from `patterns.py` — the same matcher Phase 2 targeting already relies on. |
| 7 | **Candidate-path scoping in `suggested_patch.py`.** The original aggregation pulled in every renamed-file candidate platform-wide for every suggested patch, regardless of whether that parser actually depended on the renamed file. Candidates are now filtered to only the old/removed paths that match the specific parser's own declared path dependencies (falls back to the old unscoped behavior only if no registry is supplied, since a noisy suggestion is more recoverable than an empty one). |
| 8 | **`apply_approved_patch()` guards against a missing table.** The original raised a raw `KeyError` if a patch referenced a table not present in the parser config (e.g. a stale config). Now raises a clear `ValueError` naming the patch ID, the missing table, and the config path. |

## Quick start

```bash
python -m update_trap.app
```

1. Set the scope (source profile, targets, structured-key kinds, optional manual include/exclude patterns).
2. Create or load a **baseline** snapshot.
3. Create or load a **new** snapshot (same scope, later point in time).
4. Run the diff.
5. Export the claim pack.
6. (Optional) Run the parser breakage check against a `parser_registry.json` and signature library — produces `parser_breakage_assessment.json`, `signature_advisory.json`, and the readiness dashboard.
7. (Optional) Generate the court exhibit pack from the claim pack bundle.

## Observed vs. inferred

Every output in Update Trap is explicitly labeled:

- **Observed:** file presence/absence, file hash changes, SQLite schema diffs, structured-key diffs.
- **Inferred:** candidate path suggestions (basename match only), signature advisory correlation (non-deterministic), parser risk assessment.

This separation is preserved end to end — into the claim pack, into the dashboard, and into the court exhibit pack.
