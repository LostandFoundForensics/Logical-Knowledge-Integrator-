# Pattern Harvester

**Find emails, phones, URLs, and IPs in files — read-only.**

Point at a file or folder dump. Results go to `--out`, never back into evidence.

## Use

```bash
python -m pattern_harvester list
python -m pattern_harvester scan /path/to/dump --out ./ph_out
python -m pattern_harvester scan ./image.bin --scanners email,url --out ./ph_out
```

## Scanners

| id | Label |
|----|-------|
| `email` | Email addresses |
| `phone` | Phone numbers (E.164 + NANP-like) |
| `url` | http/https URLs |
| `ip` | IPv4 addresses |

## Rules

- Evidence opened **read-only**
- Pattern matches ≠ verified identities
- Outputs only under `--out`
- Feeds **Bardo** via JSONL if you want case aggregation

---
*LoKi Platform — Lost & Found Forensics*
