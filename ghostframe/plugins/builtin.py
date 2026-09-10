"""
Built-in Ghostframe plugins.

Plain-language labels. Volatility-backed when available; otherwise clear messages.
No training required: the label says what you get.
"""
from __future__ import annotations

from typing import List

from ghostframe.core.plugin_contract import (
    GhostframePlugin,
    PluginResult,
    PluginSpec,
    RunContext,
)
from ghostframe.adapters.volatility3_adapter import Volatility3Adapter
from ghostframe.registry import PluginRegistry


class _VolPlugin(GhostframePlugin):
    """Base for plugins that try a list of Volatility plugin names."""

    vol_candidates: List[str] = []

    def run(self, ctx: RunContext) -> PluginResult:
        adapter = Volatility3Adapter()
        if not adapter.available():
            return PluginResult(
                ok=False,
                plugin_id=self.spec.plugin_id,
                warnings=[
                    "Volatility 3 is not installed. "
                    "Install with: pip install volatility3"
                ],
            )
        outcome = adapter.run_plugin_best_effort(
            ctx=ctx,
            plugin_candidates=self.vol_candidates,
        )
        return PluginResult(
            ok=outcome.ok,
            plugin_id=self.spec.plugin_id,
            rows=outcome.rows,
            warnings=outcome.warnings,
            notes=[
                f"backend_plugin={outcome.plugin_name}" if outcome.plugin_name else ""
            ],
        )


class ProcessListPlugin(_VolPlugin):
    spec = PluginSpec(
        plugin_id="processes",
        label="List running processes",
        description="Shows processes that were running when the memory was captured.",
        category="processes",
        requires_volatility=True,
    )
    vol_candidates = [
        "windows.pslist.PsList",
        "linux.pslist.PsList",
        "mac.pslist.PsList",
    ]


class NetworkConnectionsPlugin(_VolPlugin):
    spec = PluginSpec(
        plugin_id="network",
        label="Network connections",
        description="Shows network connections found in memory.",
        category="network",
        requires_volatility=True,
    )
    vol_candidates = [
        "windows.netscan.NetScan",
        "linux.sockstat.Sockstat",
        "mac.netstat.Netstat",
    ]


class CommandLinesPlugin(_VolPlugin):
    spec = PluginSpec(
        plugin_id="cmdline",
        label="Process command lines",
        description="Shows the full command line used to start each process.",
        category="processes",
        requires_volatility=True,
    )
    vol_candidates = [
        "windows.cmdline.CmdLine",
        "linux.psaux.PsAux",
    ]


class ImageInfoPlugin(_VolPlugin):
    spec = PluginSpec(
        plugin_id="imageinfo",
        label="What kind of memory is this?",
        description="Identifies the operating system and basic facts about the capture.",
        category="os",
        requires_volatility=True,
    )
    vol_candidates = [
        "windows.info.Info",
        "linux.banner.Banner",
        "mac.bash.Bash",  # fallback probe; may fail on non-mac
    ]


class EvidenceHashPlugin(GhostframePlugin):
    """Works without Volatility — always available."""

    spec = PluginSpec(
        plugin_id="hash",
        label="Fingerprint this memory file",
        description="Calculates a SHA-256 fingerprint so you can prove the file did not change.",
        category="os",
        requires_volatility=False,
    )

    def run(self, ctx: RunContext) -> PluginResult:
        return PluginResult(
            ok=True,
            plugin_id=self.spec.plugin_id,
            rows=[
                {
                    "path": ctx.evidence_path,
                    "sha256": ctx.evidence_sha256,
                    "note": "Read-only fingerprint. Evidence was not modified.",
                }
            ],
            notes=["Evidence opened read-only for hashing only."],
        )


def register_builtins(reg: PluginRegistry) -> None:
    for cls in (
        EvidenceHashPlugin,
        ImageInfoPlugin,
        ProcessListPlugin,
        CommandLinesPlugin,
        NetworkConnectionsPlugin,
    ):
        reg.register(cls())
