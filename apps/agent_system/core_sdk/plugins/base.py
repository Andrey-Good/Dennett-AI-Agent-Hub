from __future__ import annotations

import json
import hashlib
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel
from packaging.version import Version, InvalidVersion

from ..enums import PluginKind


class DependencySpec(BaseModel):
    type: str
    name: str
    version: Optional[str] = None
    spec: Optional[str] = None


class BasePlugin:
    """Базовый класс для всех плагинов."""

    PLUGIN_KIND: ClassVar[PluginKind]
    PLUGIN_ID: ClassVar[str]
    PLUGIN_NAME: ClassVar[str]
    PLUGIN_VERSION: ClassVar[str]

    DESCRIPTION: ClassVar[str] = ""
    CATEGORY: ClassVar[str] = "General"
    ICON: ClassVar[Optional[str]] = None

    # "auto" | "core" | "uv" | True | False
    EXECUTION_MODE: ClassVar[Union[str, bool]] = "auto"

    SDK_VERSION_REQUIRED: ClassVar[Optional[str]] = None
    CORE_VERSION_REQUIRED: ClassVar[Optional[str]] = None

    DEPENDENCIES: ClassVar[List[Union[Dict[str, Any], str]]] = []
    PERMISSIONS: ClassVar[List[str]] = []

    class ConfigModel(BaseModel):
        pass

    @classmethod
    def _normalize_execution_mode(cls) -> str:
        value = cls.EXECUTION_MODE
        if value is True:
            return "core"
        if value is False:
            return "uv"
        if value not in ("auto", "core", "uv"):
            raise ValueError(f"Invalid EXECUTION_MODE: {value!r}")
        return value

    @classmethod
    def _normalize_dependencies(cls) -> List[DependencySpec]:
        items: List[DependencySpec] = []
        for item in cls.DEPENDENCIES:
            if isinstance(item, str):
                name = (
                    item.split("==")[0]
                    .split(">")[0]
                    .split("<")[0]
                    .split("!")[0]
                    .strip()
                )
                items.append(DependencySpec(type="python", name=name, spec=item))
            elif isinstance(item, dict):
                items.append(DependencySpec(**item))
            else:
                raise TypeError(f"Unsupported dependency format: {item!r}")
        return items

    @classmethod
    def validate_meta(cls) -> None:
        if not cls.PLUGIN_ID:
            raise ValueError("PLUGIN_ID must not be empty")
        if not cls.PLUGIN_NAME:
            raise ValueError("PLUGIN_NAME must not be empty")
        if not cls.PLUGIN_VERSION:
            raise ValueError("PLUGIN_VERSION must not be empty")
        try:
            Version(cls.PLUGIN_VERSION)
        except InvalidVersion as exc:
            raise ValueError(f"PLUGIN_VERSION invalid: {cls.PLUGIN_VERSION!r}") from exc

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return cls.ConfigModel.model_json_schema()

    @classmethod
    def validate_config(cls, raw: Optional[Dict[str, Any]]) -> "BasePlugin.ConfigModel":
        if raw is None:
            raw = {}
        return cls.ConfigModel.model_validate(raw)

    @classmethod
    def get_spec(cls) -> Dict[str, Any]:
        cls.validate_meta()
        deps = cls._normalize_dependencies()
        execution_mode = cls._normalize_execution_mode()

        dependencies_payload = [
            {"type": d.type, "name": d.name, "version": d.version, "spec": d.spec}
            for d in deps
        ]

        return {
            "meta": {
                "spec_version": 1,
                "kind": cls.PLUGIN_KIND.value,
                "id": cls.PLUGIN_ID,
                "name": cls.PLUGIN_NAME,
                "version": cls.PLUGIN_VERSION,
                "description": cls.DESCRIPTION,
                "category": cls.CATEGORY,
                "icon": cls.ICON,
            },
            "compatibility": {
                "sdk_version_required": cls.SDK_VERSION_REQUIRED,
                "core_version_required": cls.CORE_VERSION_REQUIRED,
            },
            "permissions": {"items": list(cls.PERMISSIONS)},
            "dependencies": {"items": dependencies_payload},
            "schemas": {"config": cls.get_config_schema()},
            "runtime": {
                "is_long_running": False,
                "cancellable": True,
                "execution_mode": execution_mode,
            },
        }

    @classmethod
    def fingerprint(cls) -> str:
        spec = cls.get_spec()
        payload = json.dumps(
            spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
