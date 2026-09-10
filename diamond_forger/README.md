# Diamond Forger

**Authorized hash recovery — dry-run by default.**

Consumes verifier lines from **LockBreaker** (e.g. `$itunes_backup$…`) and lab
`sha256:` digests. Real dictionary attempts require examiner + authority and
`--execute`.

Not a silent cracker. Not a full Hashcat GPU stack.

## Use

```bash
python -m diamond_forger formats

# dry-run (default)
python -m diamond_forger check '$itunes_backup$9$...'

# authorized bounded dictionary
python -m diamond_forger check 'sha256:...' \
  --execute \
  --examiner 'Jane Doe' \
  --authority 'Warrant 2024-001' \
  --wordlist ./words.txt \
  --out ./df_out
```

## Formats

| id | Purpose |
|----|---------|
| `itunes_backup` | LockBreaker iOS backup verifier lines |
| `sha256_utf8` | Lab/training SHA-256 of UTF-8 password |

## Rules

| Rule | Meaning |
|------|---------|
| Dry-run default | No guesses without `--execute` |
| Authority gate | Examiner + authority strings required |
| Bounded | `--max-attempts` cap |
| Sensitive output | Plaintext only in `--out` JSON when recovered |

---
*LoKi Platform — Lost & Found Forensics*
