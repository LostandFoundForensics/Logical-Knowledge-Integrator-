# Chop Shop

**Portable LoKi workbench** (Santoku-class *role* — not a full Linux distro).

Chop Shop stages a case **bench**, probes which tools import on this host, and
points operators at the right station (intake → access → android/ios → case).

## Use

```bash
export PYTHONPATH=/path/to/loki_complete

python -m chopshop stations
python -m chopshop probe
python -m chopshop bench ./my_bench --case CASE-001 --examiner 'Jane Doe'
python -m chopshop recommend android
```

## Bench layout

```
my_bench/
  bench.json
  evidence_links/   # path notes only — prefer not to copy bulk evidence here
  out/              # tool outputs
  notes/            # authority / examiner notes
  exports/          # handoff packages
  logs/
```

## Stations

| id | Tools |
|----|--------|
| intake | EchoReader, Nimbus Bridge |
| access | LockBreaker, Diamond Forger |
| android | Excavator, Memory Snare |
| ios | iDriller, Recall Engine |
| bulk | Pattern Harvester, Truth Relic, Integrity Breaker |
| case | Bardo, ChronoChain, Sundial, Witness Light |
| qa | Truthloom, Update Trap |

Then run: `python -m loki case ./my_bench/out/run1 --android <dump>`

---
*LoKi Platform — Lost & Found Forensics*
