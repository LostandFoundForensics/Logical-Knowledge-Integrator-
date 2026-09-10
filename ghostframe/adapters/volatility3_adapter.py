"""
Volatility 3 library adapter for Ghostframe.

Uses the public Volatility 3 library API only (context → automagic →
construct_plugin → run → TreeGrid). No shell-outs. Evidence is referenced
by file: URI and never written.

If volatility3 is not installed, available() is False and callers get a
clear warning instead of a crash.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ghostframe.core.plugin_contract import RunContext
from ghostframe.adapters.vol3_treegrid import treegrid_to_rows


@dataclass
class Vol3RunOutcome:
    ok: bool
    plugin_name: str
    plugin_class_name: str
    warnings: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)


class Volatility3Adapter:
    """In-process bridge to Volatility 3. Never modifies the memory image."""

    # Cache: (image_sha256, plugin_name) → outcome. Memory analysis is expensive.
    _RESULT_CACHE: Dict[tuple, Vol3RunOutcome] = {}

    def __init__(self) -> None:
        self._available = False
        try:
            import volatility3  # noqa: F401
            self._available = True
        except Exception:
            self._available = False

    def available(self) -> bool:
        return self._available

    @classmethod
    def clear_cache(cls) -> None:
        cls._RESULT_CACHE.clear()

    def run_plugin(
        self,
        *,
        ctx: RunContext,
        plugin_name: str,
        progress: Optional[Callable[[float, str], None]] = None,
        max_rows: int = 100_000,
    ) -> Vol3RunOutcome:
        """Run a single Volatility plugin by dotted name (e.g. windows.pslist.PsList)."""
        return self.run_plugin_best_effort(
            ctx=ctx,
            plugin_candidates=[plugin_name],
            progress=progress,
            max_rows=max_rows,
        )

    def run_plugin_best_effort(
        self,
        *,
        ctx: RunContext,
        plugin_candidates: List[str],
        base_config_path: str = "plugins",
        progress: Optional[Callable[[float, str], None]] = None,
        max_rows: int = 100_000,
    ) -> Vol3RunOutcome:
        """
        Try plugin names in order; return the first that succeeds.
        Results are cached per (evidence hash, plugin name).
        """
        if not self._available:
            return Vol3RunOutcome(
                ok=False,
                plugin_name="",
                plugin_class_name="",
                warnings=["volatility3 is not installed. pip install volatility3"],
                rows=[],
            )

        for name in plugin_candidates:
            cache_key = (ctx.evidence_sha256, name)
            if cache_key in self._RESULT_CACHE:
                return self._RESULT_CACHE[cache_key]

        from volatility3 import framework
        from volatility3 import plugins as v3plugins
        from volatility3.framework import contexts, automagic
        from volatility3.framework.configuration import path_join

        try:
            framework.require_interface_version(2, 0, 0)
        except Exception:
            try:
                framework.require_interface_version(1, 0, 0)
            except Exception as e:
                return Vol3RunOutcome(
                    ok=False,
                    plugin_name="",
                    plugin_class_name="",
                    warnings=[f"Volatility framework version check failed: {e}"],
                    rows=[],
                )

        failures = framework.import_files(v3plugins, True)
        warnings: List[str] = []
        if failures:
            warnings.append(f"{len(failures)} volatility plugin module(s) failed to import.")

        plugin_list = framework.list_plugins()
        evidence_path = Path(ctx.evidence_path).resolve()
        if not evidence_path.is_file():
            return Vol3RunOutcome(
                ok=False,
                plugin_name="",
                plugin_class_name="",
                warnings=[f"Evidence file not found: {evidence_path}"],
                rows=[],
            )
        evidence_url = f"file:{evidence_path.as_posix()}"

        progress_cb = progress or (lambda _pct, _desc: None)

        for plugin_name in plugin_candidates:
            if plugin_name not in plugin_list:
                warnings.append(f"Plugin not found: {plugin_name}")
                continue

            plugin_class = plugin_list[plugin_name]
            class_name = plugin_class.__name__

            vctx = contexts.Context()
            # LayerStacker looks at automagic.LayerStacker.single_location
            vctx.config["automagic.LayerStacker.single_location"] = evidence_url
            plugin_config_path = path_join(base_config_path, class_name)
            vctx.config[path_join(plugin_config_path, "single_location")] = evidence_url

            available_ams = automagic.available(vctx)
            chosen_ams = automagic.choose_automagic(available_ams, plugin_class)
            am_errors = automagic.run(
                chosen_ams, vctx, plugin_class, base_config_path,
                progress_callback=progress_cb,
            )
            if am_errors:
                warnings.append(f"Automagic reported {len(am_errors)} issue(s) for {plugin_name}")

            try:
                constructed = framework.plugins.construct_plugin(
                    vctx,
                    chosen_ams,
                    plugin_class,
                    base_config_path,
                    progress_cb,
                    file_consumer=None,
                )
                treegrid = constructed.run()
                rows = treegrid_to_rows(treegrid, max_rows=max_rows)
                outcome = Vol3RunOutcome(
                    ok=True,
                    plugin_name=plugin_name,
                    plugin_class_name=class_name,
                    warnings=list(warnings),
                    rows=rows,
                )
                self._RESULT_CACHE[(ctx.evidence_sha256, plugin_name)] = outcome
                return outcome
            except Exception as e:
                warnings.append(f"{plugin_name} failed: {type(e).__name__}: {e}")
                continue

        return Vol3RunOutcome(
            ok=False,
            plugin_name="",
            plugin_class_name="",
            warnings=warnings or ["No candidate plugin succeeded."],
            rows=[],
        )
