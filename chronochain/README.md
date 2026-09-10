# ChronoChain

**One timeline from many sources. Read-only on evidence. Plain language.**

ChronoChain collects events (SMS, calls, and more), stores them in a case
timeline, links events that happened close together, and exports a CSV a
non-expert can open.

## Use

```bash
# 1. Start a case timeline
python -m chronochain init ./my_case

# 2. Add SMS from an Android database (opened read-only)
python -m chronochain add-sms ./my_case /path/to/mmssms.db

# 3. Link nearby events
python -m chronochain correlate ./my_case

# 4. Export for review
python -m chronochain export ./my_case --csv timeline.csv

# Check status
python -m chronochain status ./my_case
```

## Design rules

| Rule | Meaning |
|------|---------|
| Manual-first | You choose what to add and when to correlate |
| Read-only evidence | SMS DBs opened with SQLite `mode=ro` |
| Working DB is ours | `timeline.db` lives in the case folder we create |
| Observations only | Links mean “happened near each other”, not guilt |
| Plain export | CSV columns: when, category, title, description, actors |

## Layout

```
chronochain/
  core/       schema + time normalization
  ingest/     SMS/calls (RO) and generic JSON
  store.py    case timeline database
  correlation.py
  export.py
  cli.py
```

---
*LoKi Platform — Lost & Found Forensics*
