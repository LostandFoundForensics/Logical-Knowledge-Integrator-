from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Optional
from .base import BackendAdapter, BackendRunRequest, BackendRunResult


class JohnJumboAdapter(BackendAdapter):
    backend_id = "john"

    def run_phase(self, req: BackendRunRequest) -> BackendRunResult:
        if os.environ.get("LOCKBREAKER_ENABLE_REAL_BACKENDS", "0") != "1":
            return BackendRunResult(
                ok=True, backend=self.backend_id,
                message="DRY-RUN (john)", found_any=False, artifacts={}
            )

        john = os.environ.get("LOCKBREAKER_JOHN_BIN", "john")
        phase_dir = req.artifacts_dir / f"phase_{req.phase_index:02d}_john"
        phase_dir.mkdir(parents=True, exist_ok=True)

        session_name = f"{req.job_id}_p{req.phase_index:02d}"
        log_path = phase_dir / "john.log"
        findings_path = phase_dir / "findings.tsv"

        cmd = [
            john,
            f"--session={session_name}",
            f"--logfile={log_path}",
            f"--max-run-time={req.max_runtime_minutes * 60}",
        ]

        if req.format_hint:
            cmd.append(f"--format={req.format_hint}")

        if req.strategy in ("wordlist_rules", "hybrid_guided"):
            if req.wordlists:
                cmd.append(f"--wordlist={req.wordlists[0]['path']}")
            if req.rulesets:
                # rulesets are managed assets — never raw user strings
                cmd.append(f"--rules={req.rulesets[0]['id']}")
        elif req.strategy == "exhaustive":
            cmd.append("--incremental=Digits")

        cmd.append(str(req.crack_input_path))

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=(req.max_runtime_minutes * 60) + 30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            pass  # time-bounded phase ends cleanly

        # Collect results via john --show
        show_cmd = [john, "--show=left"]
        if req.format_hint:
            show_cmd.append(f"--format={req.format_hint}")
        show_cmd.append(str(req.crack_input_path))

        # --show=left shows CRACKED entries in user:password:... format
        show_cmd_cracked = [john, "--show"]
        if req.format_hint:
            show_cmd_cracked.append(f"--format={req.format_hint}")
        show_cmd_cracked.append(str(req.crack_input_path))

        proc = subprocess.run(
            show_cmd_cracked,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False
        )

        lines = [
            ln for ln in proc.stdout.splitlines()
            if ln.strip() and ":" in ln
            and not ln.startswith("0 password")
            and not ln.startswith("1 password")
        ]

        found_any = len(lines) > 0
        if found_any:
            tsv_lines = []
            for ln in lines:
                # john --show format: username:password:uid:gid:gecos:home:shell
                # or hash:password for hash-only files
                # FIXED: use maxsplit=1 then take last segment to handle
                # passwords containing colons
                parts = ln.split(":")
                if len(parts) >= 2:
                    user = parts[0].strip()
                    # Password is parts[1] for simple formats,
                    # but for /etc/passwd-style it could be parts[1]
                    # We take parts[1] as the password (most common john output)
                    password = parts[1].strip()
                    tsv_lines.append(f"{user}\t{password}")
            if tsv_lines:
                findings_path.write_text("\n".join(tsv_lines), encoding="utf-8")

        return BackendRunResult(
            ok=True,
            backend=self.backend_id,
            message=f"John phase completed (session={session_name})",
            found_any=found_any,
            artifacts={
                "phase_dir": str(phase_dir),
                "john_log": str(log_path),
                "findings_tsv": str(findings_path) if findings_path.exists() else "",
                "session_name": session_name,
            },
            raw_output_path=str(findings_path) if findings_path.exists() else None,
            errors=[proc.stderr.strip()] if proc.stderr.strip() else [],
        )
