# Truth Relic

**Read-only filesystem inventory and disk image probe.**

- Folders: list paths, sizes, times, optional SHA-256  
- Images: MBR/GPT partition map + filesystem signature hints  
- **Never mounts. Never writes evidence.**

The large experimental `truthrelicquery.py` remains as a reference for deeper
ext4/APFS work. This package is the stable, importable operator path.

## Use

```bash
python -m truthrelic actions
python -m truthrelic inventory /path/to/folder --out ./tr_out
python -m truthrelic inventory /path/to/folder --hash --out ./tr_out
python -m truthrelic probe /path/to/disk.img --out ./tr_out
python -m truthrelic hash /path/to/evidence.bin
```

## Rules

| Rule | Meaning |
|------|---------|
| Read-only | Only `open(..., "rb")` / `lstat` on evidence |
| No mount | Partition map is metadata, not a live FS |
| Bounded | Optional partial hash via `--max-hash-bytes` |
| Outputs outside evidence | `--out` case folder only |

---
*LoKi Platform — Lost & Found Forensics*
