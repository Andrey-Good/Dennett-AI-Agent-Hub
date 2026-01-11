"""
Пример ноды: сумматор двух чисел.
EXECUTION_MODE = "auto" — может запуститься в core или uv.
"""

from pydantic import BaseModel
from core_sdk.plugins.node import BaseNode
from core_sdk.context import NodeContext


class SumNode(BaseNode):
    PLUGIN_ID = "math.sum"
    PLUGIN_NAME = "Sum"
    PLUGIN_VERSION = "1.0.0"
    DESCRIPTION = "Adds two numbers"
    CATEGORY = "Math"
    ICON = None

    EXECUTION_MODE = "auto"
    DEPENDENCIES = []

    class ConfigModel(BaseModel):
        pass

    class InputModel(BaseModel):
        a: float
        b: float

    class OutputModel(BaseModel):
        result: float

    def run(self, ctx: NodeContext, inputs: InputModel) -> OutputModel:
        ctx.logger.info(f"Adding {inputs.a} + {inputs.b}")
        return self.OutputModel(result=inputs.a + inputs.b)


PLUGIN_CLASS = SumNode
