"""
Minimal case pipeline — Android folder dump and/or iOS backup.

Runs available tools sequentially; skips missing modules gracefully.
All tool outputs land under case_dir/out/<tool>/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _run_module(
    module: str,
    args: List[str],
    *,
    root: Path,
    extra_pythonpath: str = "",
) -> Dict:
    env = os.environ.copy()
    paths = [str(root)]
    if extra_pythonpath:
        paths.insert(0, str(root / extra_pythonpath))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(paths + ([existing] if existing else []))
    cmd = [sys.executable, "-m", module, *args]
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "module": module,
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
            "ok": proc.returncode == 0,
        }
    except Exception as e:
        return {
            "module": module,
            "cmd": cmd,
            "returncode": -1,
            "ok": False,
            "error": str(e),
        }


def run_case(
    case_dir: Path,
    *,
    android_dump: Optional[Path] = None,
    ios_backup: Optional[Path] = None,
    takeout: Optional[Path] = None,
    root: Optional[Path] = None,
) -> Dict:
    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    out_root = case_dir / "out"
    out_root.mkdir(exist_ok=True)
    root = Path(root or Path(__file__).resolve().parents[1])
    steps: List[Dict] = []

    if android_dump:
        android_dump = Path(android_dump)
        for mod, extra, args in [
            ("android_excavator", "", ["extract", str(android_dump), "--out", str(out_root / "android_excavator")]),
            ("memory_snare", "", ["scan", str(android_dump), "--out", str(out_root / "memory_snare")]),
            ("pattern_harvester", "", ["scan", str(android_dump), "--out", str(out_root / "pattern_harvester")]),
            ("integrity_breaker", "", ["scan", str(android_dump), "--out", str(out_root / "integrity_breaker")]),
            ("truthrelic", "", ["inventory", str(android_dump), "--out", str(out_root / "truthrelic")]),
        ]:
            steps.append(_run_module(mod, args, root=root, extra_pythonpath=extra))

    if ios_backup:
        ios_backup = Path(ios_backup)
        steps.append(
            _run_module(
                "echoreader",
                ["inspect", str(ios_backup), "--out", str(out_root / "echoreader")],
                root=root,
            )
        )
        steps.append(
            _run_module(
                "idriller",
                ["extract", str(ios_backup), "--out", str(out_root / "idriller")],
                root=root,
            )
        )
        steps.append(
            _run_module(
                "recall_engine",
                ["scan", str(ios_backup), "--out", str(out_root / "recall_engine")],
                root=root,
            )
        )

    if takeout:
        takeout = Path(takeout)
        steps.append(
            _run_module(
                "nimbus_bridge",
                ["scan", str(takeout), "--out", str(out_root / "nimbus_bridge")],
                root=root,
                extra_pythonpath="nimbus_bridge",
            )
        )

    # Optional: draft report if any non-empty artifacts.jsonl exists
    for candidate in [
        out_root / "memory_snare" / "artifacts.jsonl",
        out_root / "idriller" / "artifacts.jsonl",
        out_root / "recall_engine" / "artifacts.jsonl",
        out_root / "android_excavator" / "artifacts.jsonl",
    ]:
        if candidate.is_file() and candidate.stat().st_size > 0:
            steps.append(
                _run_module(
                    "witness_light",
                    [
                        "draft",
                        "--artifacts",
                        str(candidate),
                        "--case",
                        case_dir.name,
                        "--out",
                        str(out_root / "witness_light"),
                    ],
                    root=root,
                )
            )
            break

    # Bardo case store from all tool JSONL under out/
    bardo_db = case_dir / "bardo_case.sqlite"
    steps.append(
        _run_module(
            "bardo",
            [
                "ingest",
                "--db", str(bardo_db),
                "--from-dir", str(out_root),
                "--case", case_dir.name,
            ],
            root=root,
        )
    )

    summary = {
        "case_dir": str(case_dir.resolve()),
        "android_dump": str(android_dump) if android_dump else None,
        "ios_backup": str(ios_backup) if ios_backup else None,
        "takeout": str(takeout) if takeout else None,
        "steps": steps,
        "ok_count": sum(1 for s in steps if s.get("ok")),
        "fail_count": sum(1 for s in steps if not s.get("ok")),
    }
    (case_dir / "pipeline_report.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary
