from __future__ import annotations

from typing import Dict, List, Literal, Optional
from dataclasses import dataclass

from .static_analyzer import StaticAnalysisReport
from .compatibility import CompatibilityChecker


@dataclass
class ResolvedRuntime:
    mode: Literal["core", "uv"]
    reason: str
    is_forced: bool = False


class RuntimeResolver:
    """Решает, в каком режиме запускать плагин: core или uv."""

    def __init__(self, bundled_manifest: Dict[str, str]):
        self.bundled_manifest = bundled_manifest
        self.checker = CompatibilityChecker(bundled_manifest)

    def resolve(
        self,
        execution_mode: str,
        static_report: StaticAnalysisReport,
        plugin_deps: List[Dict[str, Optional[str]]],
    ) -> ResolvedRuntime:
        mode = execution_mode.lower()
        if mode not in ("core", "uv", "auto"):
            mode = "auto"

        if mode == "core":
            is_compat, conflicts = self.checker.check_compatible(plugin_deps)
            if not is_compat:
                return ResolvedRuntime(
                    mode="core",
                    reason=f"Core requested but incompatible: {conflicts}",
                    is_forced=True,
                )
            if not static_report.top_level_ok:
                return ResolvedRuntime(
                    mode="core",
                    reason=f"Core requested but has violations: {static_report.violations}",
                    is_forced=True,
                )
            return ResolvedRuntime(
                mode="core",
                reason="Core mode requested and compatible",
                is_forced=True,
            )

        if mode == "uv":
            return ResolvedRuntime(mode="uv", reason="Uv mode forced", is_forced=True)

        # auto
        is_compat, conflicts = self.checker.check_compatible(plugin_deps)
        if not is_compat:
            return ResolvedRuntime(
                mode="uv",
                reason=f"Auto: incompatible deps, falling back to uv: {conflicts}",
            )
        if not static_report.top_level_ok:
            return ResolvedRuntime(
                mode="uv",
                reason="Auto: top-level violations, falling back to uv",
            )
        return ResolvedRuntime(mode="core", reason="Auto: compatible and valid")
