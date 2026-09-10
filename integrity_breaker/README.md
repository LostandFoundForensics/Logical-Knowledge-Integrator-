# Integrity Breaker

**Indicator / IOC scan over folder dumps — read-only.**

Looks for path and content patterns that deserve human review (MVT-class *spirit*).
Hits are **indicators**, not a determination that a device is compromised.

## Use

```bash
python -m integrity_breaker rules
python -m integrity_breaker scan /path/to/dump --out ./ib_out
```

## Rules (built-in examples)

- Launch agent/daemon path segments  
- `authorized_keys`  
- Magisk/SuperSU-like paths  
- `.mobileconfig` / ConfigurationProfiles  
- Long base64-like runs / odd URL schemes (high FP)

## Rules of engagement

| Rule | Meaning |
|------|---------|
| Read-only | No writes into evidence |
| No auto-verdict | Output is for examiner review |
| Bounded | File count and size limits |

---
*LoKi Platform — Lost & Found Forensics*
