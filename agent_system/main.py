import asyncio
import uvicorn
from dennett.api.server import app
from dennett.core.db import DatabaseManager
from dennett.core.priority import PriorityPolicy
from dennett.core.recovery import StartupRecovery
from dennett.core.eventhub import EventHub
from dennett.workers.agent_worker import AgentWorker
from dennett.workers.inference_worker import CommunityInferenceWorker
from dennett.runners.model_runner import ModelRunner
# Импорты из вашего старого ядра (убедитесь, что они работают)
from ai_core.logic.agent_executor import AgentExecutor
# Если NodeRegistry и ArtifactManager нет в ai_core.logic, используйте заглушки или правильные импорты
try:
    from ai_core.logic import NodeRegistry, ArtifactManager
except ImportError:
    # Заглушки, если старые классы не находятся
    class NodeRegistry: pass
    class ArtifactManager: pass

# Заглушка для модели (пока не подключили реальную)
class DummyModelRunner(ModelRunner):
    async def ensure_loaded(self, model_id: str) -> None:
        print(f"  📦 Loading model: {model_id}")
    
    async def unload(self) -> None:
        print(f"  📦 Unloading model")
    
    async def run_chat(self, *, messages, parameters, on_token=None, cancel_event=None):
        if on_token:
            for word in ["Hello", " ", "from", " ", "Dennett", "!"]:
                if cancel_event and cancel_event.is_set():
                    raise asyncio.CancelledError()
                if asyncio.iscoroutinefunction(on_token):
                    await on_token(word)
                else:
                    on_token(word)
                await asyncio.sleep(0.1)
        return {
            "text": "Hello from Dennett!",
            "finish_reason": "stop",
            "usage": {"total_tokens": 6}
        }, 10.0

async def run_workers():
    """Запуск воркеров в фоне."""
    db = DatabaseManager()
    event_hub = EventHub()
    # Инициализация registry/artifact manager (зависит от вашего ai_core)
    node_registry = NodeRegistry() 
    artifact_manager = ArtifactManager() 
    
    model_runner = DummyModelRunner(settings={})
    
    agent_worker = AgentWorker(
        db=db,
        event_hub=event_hub,
        agent_executor_class=AgentExecutor,
        node_registry=node_registry,
        artifact_manager=artifact_manager,
    )
    
    inference_worker = CommunityInferenceWorker(
        db=db,
        event_hub=event_hub,
        model_runner=model_runner,
    )
    
    # Запускаем обоих воркеров
    await asyncio.gather(
        agent_worker.run(),
        inference_worker.run(),
    )

@app.on_event("startup")
async def startup_event():
    # Запускаем воркеры как фоновую задачу при старте сервера
    asyncio.create_task(run_workers())

if __name__ == "__main__":
    print("""
    🚀 Dennett AI Core v5.0
    ========================
    Starting API server and workers...
    """)
    
    uvicorn.run(
        "dennett.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
