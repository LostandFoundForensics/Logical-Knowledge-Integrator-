# LockBreaker

**Access Surface Orchestrator — not a blind cracker.**

LockBreaker answers, in order:

1. **What lawful ways in already exist?** (pairing, backups, ADB, dumps, hashes)
2. **Is there authority to go further?** (consent / warrant / court order + reference)
3. **What material can we extract read-only?**
4. **Only then** — optional recovery (dry-run by default)

Real hashcat/john stay off until you explicitly enable them.

## Use

```bash
# What profiles exist?
python -m lockbreaker profiles

# Always start here — safe on any host
python -m lockbreaker surfaces
python -m lockbreaker surfaces --evidence-root /path/to/android_dump

# Survey-only job (no auth needed)
python -m lockbreaker run survey_only --case ./case1

# Recovery profile — authority required
python -m lockbreaker run android_pattern \
  --case ./case1 \
  --evidence-root /path/to/dump \
  --basis warrant \
  --reference WR-2026-0142 \
  --examiner "J. Doe"
```

## Why this is different

| Other tools | LockBreaker |
|-------------|-------------|
| Jump to cracking | Phase 0 surface survey first |
| Optional logging | Append-only audit ledger every step |
| Implicit trust | Explicit basis + reference_id gate |
| Silent defaults | Dry-run unless `LOCKBREAKER_ENABLE_REAL_BACKENDS=1` |
| Expert-only UX | Plain-language profiles and surfaces |

## Enable real backends (lab only)

```bash
export LOCKBREAKER_ENABLE_REAL_BACKENDS=1
export LOCKBREAKER_HASHCAT_BIN=/usr/bin/hashcat   # optional
```

Without that flag, recovery phases report honestly: **nothing was attempted**.

## Doctrine profiles

| id | Authority | Risk |
|----|-----------|------|
| `survey_only` | consent | low |
| `ios_backup_hash` | consent | medium |
| `android_pin_4` / `android_pin_6` | consent | medium |
| `android_pattern` | **warrant** | high |
| `generic_hash` | consent | medium |

## Outputs (per case folder)

- `survey.json` — access surfaces
- `result.json` — full job result
- `lockbreaker_audit.jsonl` — every action
- `work/` — extracted material (never writes into evidence)

The deeper FastAPI / worker stack remains under `lockbreaker_complete/` for service deployments.

---
*LoKi Platform — Lost & Found Forensics*
