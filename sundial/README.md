# Sundial

**The reading room** — a simple timeline for people, not just tools.

Upstream tools (Bardo, ChronoChain, Excavator, iDriller) produce events.
Sundial is where an investigator or non-technical reviewer **reads** them.

## CLI (no server)

```bash
# PYTHONPATH should include the folder that *contains* the `sundial` package:
#   export PYTHONPATH=/path/to/loki_complete/sundial

python -m sundial view --timeline ./bardo_timeline.json --case CASE-001
python -m sundial export --timeline ./bardo_timeline.json --case CASE-001 --out ./sundial_out
```

Opens `timeline.txt` (plain) and `timeline.html` (browser-friendly).

## Design rules

| Rule | Meaning |
|------|---------|
| Observed-only (CLI path) | Does not mix inferred events into the default view |
| Explicit time basis | UTC labeled when converting from unix ms |
| No guilt language | Export is a reading aid, not a verdict |
| No evidence I/O | Reads timeline JSON exports only |

## Optional web UI

The FastAPI reader under `sundial/app.py` remains for bundle-based demos:

```bash
pip install -r requirements.txt
uvicorn sundial.app:app --reload   # from this directory
```

Use the **CLI export** when you want a zero-dependency handoff file.

---
*LoKi Platform — Lost & Found Forensics*
