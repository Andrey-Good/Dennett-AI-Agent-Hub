import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Optional, Callable

class AgentWorker:
    """Worker that processes agent execution tasks."""
    
    LEASE_TTL_SEC = 600
    POLL_INTERVAL_SEC = 0.1

    def __init__(
        self,
        db,
        event_hub,
        agent_executor_class,
        node_registry,
        artifact_manager=None,
    ):
        self.db = db
        self.event_hub = event_hub
        self.agent_executor_class = agent_executor_class
        self.node_registry = node_registry
        self.artifact_manager = artifact_manager
        self.worker_lease_id = str(uuid.uuid4())
        self.running_executions: Dict[str, asyncio.Event] = {}

    async def run(self):
        """Main worker loop: poll → lease → execute → finalize."""
        print(f"🚀 AgentWorker started (lease_id={self.worker_lease_id[:8]})")
        
        while True:
            try:
                # Atomically lease one execution
                task = await self._lease_execution()
                
                if not task:
                    await asyncio.sleep(self.POLL_INTERVAL_SEC)
                    continue

                execution_id = task["execution_id"]
                agent_id = task["agent_id"]
                
                print(f"▶️  AgentWorker: starting {execution_id[:8]}")
                
                # Create cancel event
                cancel_event = asyncio.Event()
                self.running_executions[execution_id] = cancel_event

                try:
                    # Load agent config
                    agent_config = self._load_agent_config(agent_id)
                    if not agent_config:
                        raise RuntimeError(f"Agent config not found: {agent_id}")

                    # Create AgentExecutor instance
                    executor = self.agent_executor_class(
                        agent_config=agent_config,
                        execution_id=execution_id,
                        db_session=self.db,
                        registry=self.node_registry,
                        event_emitter=self._emit_node_event,
                        cancellation_token=cancel_event,
                        artifact_manager=self.artifact_manager,
                    )

                    # Run graph (CONTRACT: must call run_graph())
                    result = await executor.run_graph()

                    # Finalize: SUCCESS
                    await self._finalize_execution(
                        execution_id,
                        status="COMPLETED",
                        final_result=result
                    )
                    
                except asyncio.CancelledError:
                    await self._finalize_execution(
                        execution_id,
                        status="CANCELED"
                    )
                    
                except Exception as e:
                    error_log = traceback.format_exc()
                    await self._finalize_execution(
                        execution_id,
                        status="FAILED",
                        error_log=error_log
                    )
                    
                finally:
                    self.running_executions.pop(execution_id, None)

            except Exception as e:
                print(f"❌ AgentWorker error: {e}")
                await asyncio.sleep(self.POLL_INTERVAL_SEC)

    async def _lease_execution(self) -> Optional[Dict]:
        """Atomically lease one execution: UPDATE...RETURNING (CRITICAL: single SQL statement)"""
        query = """
            UPDATE executions
            SET
                status = 'RUNNING',
                lease_id = :lease_id,
                lease_expires_at = CAST(strftime('%s', 'now') AS INTEGER) + :lease_ttl,
                started_at = COALESCE(started_at, CAST(strftime('%s', 'now') AS INTEGER))
            WHERE execution_id = (
                SELECT execution_id
                FROM executions
                WHERE status = 'PENDING'
                ORDER BY priority DESC, enqueue_ts ASC
                LIMIT 1
            )
            RETURNING execution_id, agent_id, priority
        """
        return self.db.execute_returning(query, {
            "lease_id": self.worker_lease_id,
            "lease_ttl": self.LEASE_TTL_SEC,
        })

    async def _finalize_execution(
        self,
        execution_id: str,
        status: str,
        final_result: Optional[dict] = None,
        error_log: Optional[str] = None,
    ):
        """Write final status to DB."""
        now_ts = int(datetime.utcnow().timestamp())
        
        query = """
            UPDATE executions
            SET
                status = :status,
                completed_at = :completed_at,
                final_result = :final_result,
                error_log = :error_log
            WHERE execution_id = :execution_id
        """
        self.db.execute_update(query, {
            "execution_id": execution_id,
            "status": status,
            "completed_at": now_ts,
            "final_result": json.dumps(final_result) if final_result else None,
            "error_log": error_log,
        })
        
        print(f"✅ AgentWorker: {execution_id[:8]} → {status}")

    async def _emit_node_event(self, event: Dict):
        """Callback: emit node event to EventHub."""
        await self.event_hub.publish(
            f"execution:{event.get('execution_id')}",
            event
        )

    def _load_agent_config(self, agent_id: str) -> Optional[Dict]:
        """Load agent config from file or DB."""
        try:
            from agents.agent_loader import AgentLoader
            loader = AgentLoader()
            return loader.load(agent_id)
        except Exception as e:
            print(f"⚠️  Failed to load agent config {agent_id}: {e}")
            return None

    async def cancel_execution(self, execution_id: str):
        """Cancel running execution."""
        if execution_id in self.running_executions:
            self.running_executions[execution_id].set()
            print(f"⛔ AgentWorker: cancel requested for {execution_id[:8]}")
