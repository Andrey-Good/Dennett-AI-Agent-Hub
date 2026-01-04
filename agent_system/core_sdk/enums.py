from __future__ import annotations
from enum import Enum


class PluginKind(str, Enum):
    NODE = "node"
    TRIGGER = "trigger"


class RunStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    INTERRUPTED = "interrupted"
