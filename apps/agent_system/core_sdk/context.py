from __future__ import annotations

import logging
from typing import Any, Protocol


class CancelledError(Exception):
    """Единый тип отмены для SDK."""


class LoggerLike(Protocol):
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class BaseContext:
    def __init__(
        self,
        *,
        run_id: str,
        plugin_id: str,
        logger: LoggerLike | None = None,
        debug: bool = False,
        cancellation_token: Any | None = None,
    ) -> None:
        self.run_id = run_id
        self.plugin_id = plugin_id
        self.logger: LoggerLike = logger or logging.getLogger(f"core_sdk.{plugin_id}")
        self.debug = debug
        self._cancellation_token = cancellation_token

    def is_cancelled(self) -> bool:
        if self._cancellation_token is None:
            return False
        is_set = getattr(self._cancellation_token, "is_set", None)
        return bool(is_set()) if callable(is_set) else False

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise CancelledError("Execution cancelled")


class NodeContext(BaseContext):
    """Контекст для нод."""


class TriggerContext(BaseContext):
    """Контекст для триггеров."""

    def __init__(self, *args: Any, emitter: Any | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._emitter = emitter

    def emit(self, payload: dict, *, key: str | None = None) -> None:
        if self._emitter is None:
            self.logger.warning("TriggerContext.emit called without emitter")
            return
        event = {"key": key, "payload": payload}
        self._emitter(event)
