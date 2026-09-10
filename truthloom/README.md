# Truthloom

**Synthetic validation datasets** for LoKi parsers.

Generates labeled mini Android dumps and iOS backups so you can check that
Android Excavator, Memory Snare, iDriller, and Recall Engine still see the
expected strings after code changes.

Not real evidence. Not for production case data.

## CLI

```bash
export PYTHONPATH=/path/to/loki_complete/truthloom

python -m truthloom generate --out ./truthloom_data
python -m truthloom generate --android-only --out ./truthloom_data
python -m truthloom generate --ios-only --out ./truthloom_data
```

Then point parsers at the generated paths listed in `truthloom_index.json`.

## Ground truth

Each dataset ships a JSON manifest with `ground_truth` entries:

| artifact_type | expected substring |
|---------------|--------------------|
| android.sms / account / wifi_ssid | Truthloom… |
| ios.sms / ios.note | Truthloom… |

## Larger store API

`truthloom.cli.actions.Actions` remains for intake/quarantine workflows.
The **generate** command is the operator-facing validation path.

---
*LoKi Platform — Lost & Found Forensics*
