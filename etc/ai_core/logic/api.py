# ai_core/logic/api.py
import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from .agent_executor import (
    AgentExecutor, ArtifactManager, NodeRegistry, DBInterface
)
from .schemas import (
    ExecutionStartRequest, ExecutionStatusResponse,
    DependencyError
)

logger = logging.getLogger(__name__)

# Track running executions
_running_executions: Dict[str, asyncio.Task] = {}
_execution_cancellation_tokens: Dict[str, asyncio.Event] = {}

class AgentExecutionAPI:
    def __init__(self, db: DBInterface, registry: NodeRegistry, artifact_manager: Optional[ArtifactManager] = None):
        self.db = db
        self.registry = registry
        self.artifact_manager = artifact_manager or ArtifactManager()
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="Agent Execution API", version="5.6")

        @app.post("/api/v1/executions/run")
        async def start_execution(request: ExecutionStartRequest, background_tasks: BackgroundTasks):
            try:
                execution_id = f"exec_{uuid.uuid4().hex[:8]}"
                logger.info(f"Starting execution {execution_id}")
                
                cancellation_token = asyncio.Event()
                _execution_cancellation_tokens[execution_id] = cancellation_token

                executor = AgentExecutor(
                    agent_config=request.agent_config,
                    execution_id=execution_id,
                    db_session=self.db,
                    registry=self.registry,
                    artifact_manager=self.artifact_manager,
                    cancellation_token=cancellation_token
                )

                task = asyncio.create_task(executor.run(request.input_data))
                _running_executions[execution_id] = task
                task.add_done_callback(lambda t: self._cleanup_execution(execution_id))

                return {
                    "execution_id": execution_id,
                    "status": "RUNNING",
                    "started_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to start: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/v1/executions/{execution_id}/status")
        async def get_execution_status(execution_id: str):
            # 1. Проверяем активные задачи
            if execution_id in _running_executions:
                return {"execution_id": execution_id, "status": "RUNNING"}

            # 2. Если не активно — проверяем базу (ИСПРАВЛЕНО)
            events = await self.db.get_execution_events(execution_id)
            if events:
                # Пытаемся понять статус по последним событиям
                # В реальной системе лучше хранить статус отдельно, но для демо хватит событий
                return {
                    "execution_id": execution_id,
                    "status": "COMPLETED", # Упрощенно считаем завершенным, если есть история
                    "event_count": len(events),
                    "last_event": events[-1]["status"] if events else "UNKNOWN"
                }

            raise HTTPException(status_code=404, detail="Execution not found")

        @app.get("/health")
        async def health():
            return {"status": "ok", "version": "5.6"}

        return app

    def _cleanup_execution(self, execution_id: str):
        _running_executions.pop(execution_id, None)
        _execution_cancellation_tokens.pop(execution_id, None)

    def get_app(self) -> FastAPI:
        return self.app

def create_api(db: DBInterface, registry: NodeRegistry, artifact_manager: Optional[ArtifactManager] = None) -> FastAPI:
    api = AgentExecutionAPI(db, registry, artifact_manager)
    return api.get_app()
