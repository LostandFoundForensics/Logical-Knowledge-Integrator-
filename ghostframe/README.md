# Ghostframe

**Look inside a memory capture. Read-only. No training required.**

Ghostframe answers simple questions about a RAM image:

- What kind of system is this?
- What processes were running?
- What were their command lines?
- What network connections were open?
- What is the file’s fingerprint?

## Use

```bash
python -m ghostframe list
python -m ghostframe hash /path/to/memory.dmp
python -m ghostframe run /path/to/memory.dmp --plugins hash,processes,cmdline,network
```

Results are JSONL observations. The memory file is **never modified**.

| Rule | Meaning |
|------|---------|
| Manual-first | You choose which plugins to run |
| Read-only | Evidence opened only for reading / hashing |
| Observations only | Output is “what was seen”, not conclusions |
| Plain language | Plugin labels say what they do |

Optional: `pip install volatility3` for process/network/OS plugins.  
Without it, those plugins warn clearly; `hash` always works.

---
*LoKi Platform — Lost & Found Forensics*
