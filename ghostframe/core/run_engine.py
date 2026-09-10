"""
RunEngine — the only thing the operator needs to call after picking evidence.

1. Hash the image (read-only)
2. Build RunContext
3. Run selected plugins
4. Optionally clean / redact / sort results
5. Write JSONL observations to the case output folder
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ghostframe.core.hashing import sha256_file
from ghostframe.core.plugin_contract import GhostframePlugin, PluginResult, RunContext
from ghostframe.registry import PluginRegistry, default_registry


class RunEngine:
    def __init__(self, registry: Optional[PluginRegistry] = None) -> None:
        self.registry = registry or default_registry()

    def prepare_context(
        self,
        evidence_path: str,
        *,
        case_id: str = "",
        output_dir: str = "",
        os_hint: str = "",
        options: Optional[Dict[str, Any]] = None,
    ) -> RunContext:
        path = Path(evidence_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Memory image not found: {path}")
        digest = sha256_file(path)
        out = output_dir or str(path.parent / "ghostframe_out")
        Path(out).mkdir(parents=True, exist_ok=True)
        return RunContext(
            evidence_path=str(path),
            evidence_sha256=digest,
            case_id=case_id or path.stem,
            output_dir=out,
            os_hint=os_hint,
            options=options or {},
        )

    def run_one(self, ctx: RunContext, plugin_id: str) -> PluginResult:
        plugin = self.registry.get(plugin_id)
        return plugin.run(ctx)

    def run_many(
        self,
        ctx: RunContext,
        plugin_ids: Iterable[str],
    ) -> List[PluginResult]:
        results: List[PluginResult] = []
        for pid in plugin_ids:
            try:
                results.append(self.run_one(ctx, pid))
            except Exception as e:
                results.append(
                    PluginResult(
                        ok=False,
                        plugin_id=pid,
                        warnings=[f"Plugin crashed: {type(e).__name__}: {e}"],
                    )
                )
        return results

    def write_results(
        self,
        ctx: RunContext,
        results: List[PluginResult],
        *,
        filename: str = "observations.jsonl",
    ) -> Path:
        """Write observations only — never touch the evidence image."""
        out_path = Path(ctx.output_dir) / filename
        with out_path.open("w", encoding="utf-8") as f:
            meta = {
                "kind": "ghostframe_run_meta",
                "case_id": ctx.case_id,
                "evidence_path": ctx.evidence_path,
                "evidence_sha256": ctx.evidence_sha256,
                "created_epoch": int(time.time()),
            }
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            for r in results:
                rec = {
                    "kind": "ghostframe_plugin_result",
                    "plugin_id": r.plugin_id,
                    "ok": r.ok,
                    "row_count": r.row_count,
                    "warnings": r.warnings,
                    "notes": r.notes,
                    "rows": r.rows,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return out_path
