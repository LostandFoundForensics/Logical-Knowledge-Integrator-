# Memory Snare

**Android artifact depth from a folder dump (read-only).**

Complements **Android Excavator** (SMS/calls/contacts/chrome basics) with
accounts, browser history (Chrome epoch corrected), and Wi-Fi SSID hints.

## Use

```bash
python -m memory_snare list
python -m memory_snare scan /path/to/android_dump --out ./ms_out
python -m memory_snare scan /path --parsers accounts,browser --out ./ms_out
```

## Parsers

| id | Label |
|----|-------|
| `accounts` | System accounts.db |
| `browser` | Chrome/WebView History |
| `wifi` | SSID fields in config files |

## Rules

- Evidence SQLite: `mode=ro`
- Outputs only under `--out`
- Wi-Fi parser records names only — treat dumps as sensitive

---
*LoKi Platform — Lost & Found Forensics*
