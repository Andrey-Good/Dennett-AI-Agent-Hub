from __future__ import annotations

import ast
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .ast_validator import ASTValidator


@dataclass
class StaticAnalysisReport:
    plugin_id: str
    is_valid: bool
    top_level_ok: bool
    illegal_imports: List[str] = field(default_factory=list)
    heavy_imports: List[str] = field(default_factory=list)
    violations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "is_valid": self.is_valid,
            "top_level_ok": self.top_level_ok,
            "illegal_imports": self.illegal_imports,
            "heavy_imports": self.heavy_imports,
            "violations_count": sum(len(v) for v in self.violations.values()),
        }


class StaticAnalyzer:
    """Статический анализ plugin.py без импорта."""

    def __init__(self, plugin_path: str):
        self.plugin_path = plugin_path
        with open(plugin_path, "r", encoding="utf-8") as f:
            self.source_code = f.read()

    def analyze(self) -> StaticAnalysisReport:
        try:
            tree = ast.parse(self.source_code)
        except SyntaxError as e:
            return StaticAnalysisReport(
                plugin_id="unknown",
                is_valid=False,
                top_level_ok=False,
                violations={"syntax_error": str(e)},
            )

        plugin_id = self._extract_string_literal(tree, "PLUGIN_ID")
        validator = ASTValidator(self.source_code)
        validation = validator.validate()

        return StaticAnalysisReport(
            plugin_id=plugin_id or "unknown",
            is_valid=validation["is_valid"],
            top_level_ok=validation["is_valid"],
            heavy_imports=validation["violations"].get("heavy_imports", []),
            illegal_imports=validation["violations"].get("illegal_imports", []),
            violations=validation["violations"],
        )

    def _extract_string_literal(self, tree: ast.AST, var_name: str) -> Optional[str]:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value)
        return None

    def extract_meta(self) -> Dict[str, Any]:
        tree = ast.parse(self.source_code)
        meta: Dict[str, Any] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        value = self._extract_literal_value(node.value)
                        if value is not None:
                            meta[target.id] = value
        return meta

    @staticmethod
    def _extract_literal_value(node: ast.expr) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [StaticAnalyzer._extract_literal_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            result: Dict[Any, Any] = {}
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant):
                    result[k.value] = StaticAnalyzer._extract_literal_value(v)
            return result
        elif isinstance(node, ast.Tuple):
            return tuple(StaticAnalyzer._extract_literal_value(elt) for elt in node.elts)
        return None
