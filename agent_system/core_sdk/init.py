"""
Core SDK - главный модуль
Полный SDK для плагинов Dennett AI Core с поддержкой core/uv/auto режимов.
"""

from .enums import PluginKind, RunStatus
from .models import ErrorInfo, ArtifactRef, NodeResult, TriggerRunResult
from .context import CancelledError, BaseContext, NodeContext, TriggerContext
from .plugins import (
    BasePlugin,
    BaseNode,
    BaseTrigger,
    PluginRegistry,
    get_global_registry,
    register_plugin,
)

__version__ = "0.1.0"

__all__ = [
    "PluginKind", "RunStatus",
    "ErrorInfo", "ArtifactRef", "NodeResult", "TriggerRunResult",
    "CancelledError", "BaseContext", "NodeContext", "TriggerContext",
    "BasePlugin", "BaseNode", "BaseTrigger",
    "PluginRegistry", "get_global_registry", "register_plugin",
]
