from __future__ import annotations

from typing import Dict, List, Type

from .base import BasePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._by_id: Dict[str, Type[BasePlugin]] = {}

    def register(self, plugin_cls: Type[BasePlugin]) -> None:
        plugin_id = getattr(plugin_cls, "PLUGIN_ID", None)
        if not plugin_id:
            raise ValueError(f"Plugin class {plugin_cls.__name__} has no PLUGIN_ID")
        if plugin_id in self._by_id:
            raise ValueError(f"Plugin {plugin_id!r} already registered")
        self._by_id[plugin_id] = plugin_cls

    def get(self, plugin_id: str) -> Type[BasePlugin]:
        return self._by_id[plugin_id]

    def list(self) -> List[Type[BasePlugin]]:
        return list(self._by_id.values())

    def specs(self) -> List[dict]:
        return [cls.get_spec() for cls in self._by_id.values()]


_global_registry = PluginRegistry()


def get_global_registry() -> PluginRegistry:
    return _global_registry


def register_plugin(plugin_cls: Type[BasePlugin]) -> Type[BasePlugin]:
    _global_registry.register(plugin_cls)
    return plugin_cls
