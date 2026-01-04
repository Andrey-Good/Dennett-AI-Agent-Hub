from __future__ import annotations

from typing import Dict, List, Tuple, Optional
from packaging.requirements import Requirement
from packaging.version import Version, SpecifierSet


class CompatibilityChecker:
    """Проверяет совместимость зависимостей плагина с Core."""

    def __init__(self, bundled_manifest: Dict[str, str]):
        self.bundled_manifest = bundled_manifest

    def check_compatible(
        self,
        plugin_deps: List[Dict[str, Optional[str]]],
    ) -> Tuple[bool, List[str]]:
        conflicts: List[str] = []

        for dep in plugin_deps:
            if dep.get("type") != "python":
                continue

            spec_str = dep.get("spec")
            if not spec_str:
                continue

            try:
                req = Requirement(spec_str)
                lib_name = req.name
                core_version = self.bundled_manifest.get(lib_name)

                if core_version is None:
                    conflicts.append(f"{lib_name}: not in bundled libs")
                    continue

                if not self._is_version_compatible(core_version, req.specifier):
                    conflicts.append(
                        f"{lib_name}: core has {core_version}, "
                        f"plugin requires {req.specifier}"
                    )

            except Exception as e:
                conflicts.append(f"Failed to parse {spec_str}: {e}")

        return len(conflicts) == 0, conflicts

    @staticmethod
    def _is_version_compatible(core_version: str, specifier: SpecifierSet) -> bool:
        try:
            version = Version(core_version)
            return version in specifier
        except Exception:
            return False
