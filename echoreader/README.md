# EchoReader

**Backup intake and readiness — not a silent decryptor.**

EchoReader looks at iOS backup folders and Android `.ab` files and reports:

- Whether encryption appears to be present  
- What metadata is available  
- Sensible next tools (iDriller, Recall Engine, LockBreaker, Android Excavator)

It does **not** decrypt by default. Password recovery stays in **LockBreaker** under doctrine/authority.

## Use

```bash
python -m echoreader checks
python -m echoreader inspect /path/to/ios_backup
python -m echoreader inspect /path/to/backup.ab --out ./er_out
```

## Rules

| Rule | Meaning |
|------|---------|
| Read-only | Only reads headers / plists / presence |
| No default decrypt | Explicit recovery is a different tool |
| Honest uncertainty | Unknown encryption status is labeled |

---
*LoKi Platform — Lost & Found Forensics*
