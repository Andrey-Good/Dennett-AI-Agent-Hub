from __future__ import annotations

import traceback as _tb
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel

from ..context import NodeContext, CancelledError
from ..enums import PluginKind, RunStatus
from ..models import NodeResult, ErrorInfo
from .base import BasePlugin


class BaseNode(BasePlugin):
    PLUGIN_KIND: PluginKind = PluginKind.NODE

    class InputModel(BaseModel):
        pass

    class OutputModel(BaseModel):
        pass

    def __init__(self, config: BasePlugin.ConfigModel) -> None:
        self.config = config

    def run(
        self,
        ctx: NodeContext,
        inputs: InputModel,
    ) -> Union[OutputModel, Dict[str, Any], NodeResult]:
        raise NotImplementedError

    @classmethod
    def get_spec(cls) -> Dict[str, Any]:
        spec = super().get_spec()
        spec["schemas"]["inputs"] = cls.InputModel.model_json_schema()
        spec["schemas"]["outputs"] = cls.OutputModel.model_json_schema()
        spec["runtime"]["is_long_running"] = False
        spec["runtime"]["cancellable"] = True
        return spec

    @classmethod
    def _normalize_output(
        cls,
        raw: Union[OutputModel, Dict[str, Any], NodeResult],
    ) -> NodeResult:
        if isinstance(raw, NodeResult):
            return raw
        if isinstance(raw, BaseModel):
            payload = raw.model_dump(mode="json", exclude_none=True)
        else:
            payload = raw
        out_model = cls.OutputModel.model_validate(payload)
        return NodeResult(
            status=RunStatus.SUCCESS,
            output=out_model.model_dump(mode="json", exclude_none=True),
        )

    @classmethod
    def execute(
        cls,
        ctx: NodeContext,
        raw_inputs: Dict[str, Any],
        raw_config: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        try:
            config = cls.validate_config(raw_config)
            inputs = cls.InputModel.model_validate(raw_inputs)
        except Exception as exc:
            return NodeResult(
                status=RunStatus.ERROR,
                output=None,
                artifacts=[],
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message=str(exc),
                    traceback=_tb.format_exc() if ctx.debug else None,
                    retryable=False,
                ),
            )

        node = cls(config=config)
        try:
            ctx.raise_if_cancelled()
            result_raw = node.run(ctx, inputs)
            return cls._normalize_output(result_raw)
        except CancelledError:
            return NodeResult(status=RunStatus.INTERRUPTED, output=None, artifacts=[])
        except Exception as exc:
            return NodeResult(
                status=RunStatus.ERROR,
                output=None,
                artifacts=[],
                error=ErrorInfo(
                    code="RUNTIME_ERROR",
                    message=str(exc),
                    traceback=_tb.format_exc() if ctx.debug else None,
                ),
            )

    @classmethod
    async def execute_async(
        cls,
        ctx: NodeContext,
        raw_inputs: Dict[str, Any],
        raw_config: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        return cls.execute(ctx, raw_inputs, raw_config)
