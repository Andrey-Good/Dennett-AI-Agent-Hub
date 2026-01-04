from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import RunStatus


@dataclass
class ErrorInfo:
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    traceback: Optional[str] = None
    retryable: bool = False


@dataclass
class ArtifactRef:
    name: str
    uri: str
    media_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None


@dataclass
class NodeResult:
    status: RunStatus
    output: Optional[Dict[str, Any]] = None
    artifacts: List[ArtifactRef] = field(default_factory=list)
    error: Optional[ErrorInfo] = None


@dataclass
class TriggerRunResult:
    status: str  # "stopped" | "error"
    error: Optional[ErrorInfo] = None
