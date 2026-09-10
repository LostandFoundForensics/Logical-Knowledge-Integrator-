"""Probe which LoKi modules import and which host helpers exist."""
from __future__ import annotations

import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

# Modules expected under PYTHONPATH=loki_complete
LOKI_MODULES = [
    "lockbreaker",
    "echoreader",
    "diamond_forger",
    "android_excavator",
    "memory_snare",
    "idriller",
    "recall_engine",
    "pattern_harvester",
    "truthrelic",
    "integrity_breaker",
    "bardo",
    "chronochain",
    "ghostframe",
    "witness_light",
    "loki",
]

HOST_BINARIES = ["python3", "adb", "sqlite3", "openssl"]


def probe_environment(*, loki_root: Path | None = None) -> Dict[str, Any]:
    if loki_root:
        root = str(Path(loki_root).resolve())
        if root not in sys.path:
            sys.path.insert(0, root)

    modules: List[Dict[str, Any]] = []
    for name in LOKI_MODULES:
        try:
            mod = importlib.import_module(name)
            ver = getattr(mod, "__version__", "?")
            modules.append({"module": name, "ok": True, "version": ver})
        except Exception as e:
            modules.append({"module": name, "ok": False, "error": str(e)[:200]})

    binaries: List[Dict[str, Any]] = []
    for b in HOST_BINARIES:
        path = shutil.which(b)
        binaries.append({"name": b, "ok": path is not None, "path": path})

    # nested path modules
    nested = []
    for hint, modname in [
        ("update_trap", "update_trap"),
        ("nimbus_bridge", "nimbus_bridge"),
        ("sundial", "sundial"),
        ("truthloom", "truthloom"),
    ]:
        nested.append({"hint": hint, "module": modname, "note": f"PYTHONPATH+=…/{hint}"})

    return {
        "tool": "ChopShop",
        "python": sys.version.split()[0],
        "modules": modules,
        "binaries": binaries,
        "nested_pythonpath": nested,
        "modules_ok": sum(1 for m in modules if m["ok"]),
        "modules_fail": sum(1 for m in modules if not m["ok"]),
    }
