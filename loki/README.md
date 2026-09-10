# LoKi operator CLI

One entry point for the rebuilt tool set.

## Use

```bash
export PYTHONPATH=/path/to/loki_complete

python -m loki tools
python -m loki how android_excavator
python -m loki case ./my_case --android /path/to/android_dump
python -m loki case ./my_case --ios /path/to/ios_backup
python -m loki case ./my_case --android /dump --ios /backup --takeout /Takeout
```

## What `case` runs

**Android dump:** Excavator → Memory Snare → Pattern Harvester → Integrity Breaker → Truth Relic → Witness Light (if artifacts)

**iOS backup:** EchoReader → iDriller → Recall Engine → Witness Light (if artifacts)

**Takeout:** Nimbus Bridge

Outputs under `./my_case/out/<tool>/`. Summary: `pipeline_report.json`.

Evidence paths are only read; the case directory receives all writes.

---
*LoKi Platform — Lost & Found Forensics*
