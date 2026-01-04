from __future__ import annotations

import ast
from typing import Dict, Any, List


class ASTValidator:
    """Валидатор AST для проверки статических правил плагинов."""

    WHITELISTED_IMPORTS = {
        "core_sdk",
        "pydantic",
        "logging",
        "typing",
        "functools",
        "dataclasses",
        "enum",
        "datetime",
        "json",
        "re",
        "pathlib",
        "uuid",
        "hashlib",
        "os",
        "sys",
        "asyncio",
    }

    HEAVY_IMPORTS = {
        "numpy",
        "torch",
        "tensorflow",
        "cv2",
        "pandas",
        "sklearn",
        "scipy",
        "matplotlib",
        "PIL",
        "requests",
        "httpx",
        "aiohttp",
        "openai",
        "anthropic",
        "ollama",
    }

    def __init__(self, source_code: str):
        self.source_code = source_code
        try:
            self.tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in plugin: {e}")

    def validate(self) -> Dict[str, Any]:
        violations = {
            "top_level_calls": [],
            "top_level_control_flow": [],
            "illegal_imports": [],
            "heavy_imports": [],
        }

        for node in ast.walk(self.tree):
            if not self._is_top_level(node):
                continue
            if isinstance(node, ast.Call):
                violations["top_level_calls"].append(self._format_node(node))
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                violations["top_level_control_flow"].append(self._format_node(node))

        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in self.HEAVY_IMPORTS:
                        violations["heavy_imports"].append(module)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                module_root = module.split(".")[0]
                if module_root in self.HEAVY_IMPORTS:
                    violations["heavy_imports"].append(module_root)

        return {
            "is_valid": all(not v for v in violations.values()),
            "violations": violations,
        }

    def _is_top_level(self, node: ast.AST) -> bool:
        for parent in ast.walk(self.tree):
            if isinstance(parent, ast.Module):
                if node in parent.body:
                    return True
            elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node in parent.body:
                    return False
        return False

    @staticmethod
    def _format_node(node: ast.AST) -> str:
        if hasattr(node, "lineno"):
            try:
                src = ast.unparse(node)
            except Exception:
                src = type(node).__name__
            return f"line {node.lineno}: {src[:50]}"
        try:
            return ast.unparse(node)[:50]
        except Exception:
            return type(node).__name__
