from __future__ import annotations

import traceback as _tb
from typing import Any, Dict, Optional

from pydantic import BaseModel

from ..context import TriggerContext, CancelledError
from ..enums import PluginKind
from ..models import ErrorInfo, TriggerRunResult
from .base import BasePlugin


class BaseTrigger(BasePlugin):
    PLUGIN_KIND: PluginKind = PluginKind.TRIGGER

    class EventModel(BaseModel):
        pass

    class ConfigModel(BasePlugin.ConfigModel):
        pass

    def __init__(self, config: BasePlugin.ConfigModel) -> None:
        self.config = config

    def start(self, ctx: TriggerContext) -> None:
        raise NotImplementedError

    @classmethod
    def get_spec(cls) -> Dict[str, Any]:
        spec = super().get_spec()
        spec["schemas"]["event"] = cls.EventModel.model_json_schema()
        spec["runtime"]["is_long_running"] = True
        spec["runtime"]["cancellable"] = True
        return spec

    @classmethod
    def run_forever(
        cls,
        ctx: TriggerContext,
        raw_config: Optional[Dict[str, Any]] = None,
    ) -> TriggerRunResult:
        try:
            config = cls.validate_config(raw_config)
        except Exception as exc:
            return TriggerRunResult(
                status="error",
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message=str(exc),
                    traceback=_tb.format_exc() if ctx.debug else None,
                ),
            )

        trigger = cls(config=config)
        try:
            trigger.start(ctx)
            return TriggerRunResult(status="stopped", error=None)
        except CancelledError:
            return TriggerRunResult(status="stopped", error=None)
        except Exception as exc:
            return TriggerRunResult(
                status="error",
                error=ErrorInfo(
                    code="RUNTIME_ERROR",
                    message=str(exc),
                    traceback=_tb.format_exc() if ctx.debug else None,
                ),
            )

    @classmethod
    async def run_forever_async(
        cls,
        ctx: TriggerContext,
        raw_config: Optional[Dict[str, Any]] = None,
    ) -> TriggerRunResult:
        return cls.run_forever(ctx, raw_config)
