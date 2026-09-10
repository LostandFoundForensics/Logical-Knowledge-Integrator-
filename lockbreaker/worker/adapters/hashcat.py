from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional
from .base import BackendAdapter, BackendRunRequest, BackendRunResult

# Doctrine-driven format → hashcat mode mapping.
# These are documented attack modes — never user-configurable.
HASHCAT_MODE_MAP: Dict[str, int] = {
    # Mobile backup formats
    "FMT-IOS-ENCRYPTED-BACKUP":    14800,  # iTunes backup (PBKDF2-SHA1)
    "FMT-ANDROID-ENCRYPTED-BACKUP": 13800, # Android FDE
    # Common hash formats
    "NTLM":    1000,
    "MD5":     0,
    "SHA1":    100,
    "SHA256":  1400,
    "SHA512":  1700,
    "bcrypt":  3200,
    "WPA2":    22000,
    "WPA-PMKID": 22001,
    "PBKDF2-SHA1":   12000,
    "PBKDF2-SHA256": 10900,
    "scrypt":  8900,
    # App databases
    "SQLCipher": 24420,
}

class HashcatAdapter(BackendAdapter):
    backend_id = "hashcat"

    def run_phase(self, req: BackendRunRequest) -> BackendRunResult:
        if os.environ.get("LOCKBREAKER_ENABLE_REAL_BACKENDS", "0") != "1":
            return BackendRunResult(
                ok=True, backend=self.backend_id,
                message="DRY-RUN (hashcat)", found_any=False, artifacts={}
            )

        hc = os.environ.get("LOCKBREAKER_HASHCAT_BIN", "hashcat")

        phase_dir = req.artifacts_dir / f"phase_{req.phase_index:02d}_hashcat"
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Resolve mode from format hint or profile
        mode = self._resolve_mode(req.format_hint)
        if mode is None:
            return BackendRunResult(
                ok=False, backend=self.backend_id,
                message=f"No hashcat mode mapping for format: {req.format_hint}",
                errors=["Add format to HASHCAT_MODE_MAP in hashcat.py"],
                artifacts={},
            )

        findings_path = phase_dir / "findings.tsv"
        outfile = phase_dir / "hashcat.potfile"

        cmd = [
            hc,
            f"--hash-type={mode}",
            "--status", "--status-timer=30",
            f"--outfile={outfile}",
            "--outfile-format=2",  # hash:plain
            "--potfile-disable",   # we manage output ourselves
            f"--session={req.job_id}_p{req.phase_index:02d}",
        ]

        if req.strategy in ("wordlist_rules", "hybrid_guided"):
            cmd.append("--attack-mode=0")  # straight wordlist
            if req.wordlists:
                cmd.append(req.wordlists[0]["path"])
            if req.rulesets:
                cmd += ["--rules-file", req.rulesets[0]["path"]]
        elif req.strategy == "exhaustive":
            cmd.append("--attack-mode=3")  # brute force / mask
            cmd.append("?d?d?d?d")  # default 4-digit; override via profile

        cmd.append(str(req.crack_input_path))

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=req.max_runtime_minutes * 60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            pass

        # Normalize findings
        found_any = False
        if outfile.exists():
            lines = outfile.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
            tsv_lines = []
            for ln in lines:
                if ":" in ln:
                    parts = ln.rsplit(":", 1)
                    tsv_lines.append(f"{parts[0].strip()}\t{parts[1].strip()}")
            if tsv_lines:
                found_any = True
                findings_path.write_text("\n".join(tsv_lines), encoding="utf-8")

        return BackendRunResult(
            ok=True,
            backend=self.backend_id,
            message=f"Hashcat phase completed (mode={mode})",
            found_any=found_any,
            artifacts={"phase_dir": str(phase_dir), "outfile": str(outfile)},
            raw_output_path=str(findings_path) if findings_path.exists() else None,
            errors=[],
        )

    def _resolve_mode(self, format_hint: Optional[str]) -> Optional[int]:
        if not format_hint:
            return None
        # Direct lookup first
        if format_hint in HASHCAT_MODE_MAP:
            return HASHCAT_MODE_MAP[format_hint]
        # Case-insensitive fallback
        lc = format_hint.lower()
        for k, v in HASHCAT_MODE_MAP.items():
            if k.lower() == lc:
                return v
        return None
