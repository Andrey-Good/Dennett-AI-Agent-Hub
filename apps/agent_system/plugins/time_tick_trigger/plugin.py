"""
Пример триггера: эмитит событие каждые N секунд.
EXECUTION_MODE = "uv" — запускается в отдельном окружении.
"""

import time
from pydantic import BaseModel
from core_sdk.plugins.trigger import BaseTrigger
from core_sdk.context import TriggerContext


class TickTrigger(BaseTrigger):
    PLUGIN_ID = "time.tick"
    PLUGIN_NAME = "Tick"
    PLUGIN_VERSION = "1.0.0"
    DESCRIPTION = "Emits an event every N seconds"
    CATEGORY = "Time"

    EXECUTION_MODE = "uv"
    DEPENDENCIES = []

    class ConfigModel(BaseModel):
        interval_sec: int = 5

    class EventModel(BaseModel):
        tick: int

    def start(self, ctx: TriggerContext) -> None:
        i = 0
        while True:
            ctx.raise_if_cancelled()
            i += 1
            ctx.emit({"tick": i}, key=str(i))
            ctx.logger.info(f"Emitted tick {i}")
            time.sleep(self.config.interval_sec)


PLUGIN_CLASS = TickTrigger
