# Recall Engine

**iOS artifact depth from a standard backup (read-only).**

Complements **iDriller** (SMS / calls / contacts) with Notes, Safari history,
and Calendar events — all resolved through `Manifest.db`.

## Use

```bash
python -m recall_engine list
python -m recall_engine scan /path/to/ios_backup --out ./re_out
python -m recall_engine scan /path --parsers notes,safari --out ./re_out
```

## Parsers

| id | Label |
|----|-------|
| `notes` | Apple Notes titles |
| `safari` | Safari History.db visits |
| `calendar` | Calendar event titles |

## Rules

- `Manifest.db` and artifact DBs opened `mode=ro`
- Payload path: `<backup>/<fileID[0:2]>/<fileID>`
- Apple epoch normalized where applicable
- Outputs only under `--out`

---
*LoKi Platform — Lost & Found Forensics*
