# LightBridge

**iOS device communication surface** (libimobiledevice-class *role*).

LightBridge talks to **host tools** (`idevice_id`, `ideviceinfo`, `idevicebackup2`)
when installed. It does not reimplement usbmuxd.

When USB tools are missing — the common lab case — use an offline backup:

```text
EchoReader → iDriller / Recall Engine
```

Live backup is **dry-run by default** and requires examiner + authority.

## Use

```bash
python -m lightbridge tools
python -m lightbridge devices
python -m lightbridge info <UDID>
python -m lightbridge guide

python -m lightbridge backup <UDID> --dest ./bk \
  --examiner 'Jane Doe' --authority 'Warrant 001'          # dry-run

python -m lightbridge backup <UDID> --dest ./bk \
  --examiner 'Jane Doe' --authority 'Warrant 001' --execute
```

## Rules

| Rule | Meaning |
|------|---------|
| Host tools optional | Works without USB by guiding offline path |
| No silent pair/backup | Authority gate on live backup |
| Offline preferred | Manifest.db backups → iDriller |

---
*LoKi Platform — Lost & Found Forensics*
