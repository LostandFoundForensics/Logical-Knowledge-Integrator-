# Witness Light

**Draft observation language from tool exports — never from raw evidence.**

Witness Light is the last mile of the LoKi pipeline: turn Bardo timelines or
Excavator/iDriller JSONL into a structured draft. It only uses five sentence
classes:

- **Observed**
- **Context**
- **Consistent With**
- **Limitation**
- **Unknown**

It does **not** infer intent, motive, or guilt. A lexical policy flags forbidden phrasing.

## Use

```bash
python -m witness_light classes

python -m witness_light draft \
  --bardo-timeline ./timeline.json \
  --case CASE-001 \
  --out ./wl_out

python -m witness_light draft \
  --artifacts ./artifacts.jsonl \
  --case CASE-001 \
  --out ./wl_out
```

## Rules

| Rule | Meaning |
|------|---------|
| No evidence I/O | Only reads exports you pass in |
| Constrained language | Five sentence classes only |
| Fail-closed policy | Intent/causation phrases flagged |
| Examiner review | Draft is not a final legal product |

Legacy GUI/LLM modules (`main.py`, `llm_provider_openai.py`) remain in-tree as optional experiments; the CLI above is the stable path.

---
*LoKi Platform — Lost & Found Forensics*
