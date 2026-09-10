# Bardo Engine

**Central case brain** — ingest tool JSONL exports, store observations, export timelines.

Never opens original evidence. Only reads case **exports**.

## Use

```bash
export PYTHONPATH=/path/to/loki_complete

python -m bardo sources
python -m bardo init --case CASE-001 --db ./case.sqlite

# Auto-ingest everything under a loki case out/ folder
python -m bardo ingest --db ./case.sqlite --from-dir ./my_case/out

# Or name exports explicitly
python -m bardo ingest --db ./case.sqlite \
  --excavator ./out/android_excavator/artifacts.jsonl \
  --memory-snare ./out/memory_snare/artifacts.jsonl \
  --idriller ./out/idriller/artifacts.jsonl \
  --recall ./out/recall_engine/artifacts.jsonl \
  --pattern ./out/pattern_harvester/findings.jsonl \
  --integrity ./out/integrity_breaker/findings.jsonl \
  --nimbus ./out/nimbus_bridge/artifacts.jsonl \
  --truthrelic ./out/truthrelic/inventory.jsonl

python -m bardo status --db ./case.sqlite
python -m bardo timeline --db ./case.sqlite --out ./timeline.json
python -m bardo entities --db ./case.sqlite
python -m bardo export --db ./case.sqlite --out ./bardo_export
```

## Ingest sources

| Source | File |
|--------|------|
| Android Excavator / Memory Snare / iDriller / Recall | `artifacts.jsonl` |
| Pattern Harvester / Integrity Breaker | `findings.jsonl` |
| Nimbus Bridge | `artifacts.jsonl` |
| Truth Relic | `inventory.jsonl` |
| `--from-dir` | Discovers all of the above under a tree |

## Pipeline

```text
loki case ./case --android … --ios …
  → bardo ingest --from-dir ./case/out
  → bardo timeline / sundial / witness_light
```

---
*LoKi Platform — Lost & Found Forensics*
