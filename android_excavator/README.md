# Android Excavator

**Parse an Android folder dump. Read-only. No training required.**

Point this tool at a folder from `adb pull`, an unpacked backup, or a
userdata extract. It finds common databases and extracts observations.

This is **not** a lockscreen cracker (see LockBreaker).  
This is **not** an iOS tool (see iDriller).

## Use

```bash
# What can it extract?
python -m android_excavator list

# What databases are under this folder?
python -m android_excavator scan /path/to/android_dump

# Extract everything it knows
python -m android_excavator extract /path/to/android_dump --out ./case_out

# Only SMS and calls
python -m android_excavator extract /path/to/android_dump --parsers sms,calls --out ./case_out
```

## Parsers

| id | Label | Source examples |
|----|-------|-----------------|
| `sms` | Text messages (SMS) | `mmssms.db` |
| `calls` | Phone calls | `calllog.db`, `contacts2.db` |
| `contacts` | Address book | `contacts2.db` |
| `chrome` | Chrome web history | Chrome `History` (1601 epoch handled) |

## Rules

| Rule | Meaning |
|------|---------|
| Read-only | Every evidence SQLite opened with `mode=ro` |
| Observations only | Output is records + provenance, not conclusions |
| Plain language | `list` uses everyday labels |
| Outputs stay outside evidence | Results written only to `--out` |

---
*LoKi Platform — Lost & Found Forensics*
