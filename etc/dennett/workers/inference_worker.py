"""
CommunityInferenceWorker: Processes inference tasks sequentially.
"""

import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Optional

class CommunityInferenceWorker:
    """Worker that processes inference tasks (sequential in Community)."""
    
    LEASE_TTL_SEC = 300
    POLL_INTERVAL_SEC = 0.1

    def __init__(
        self,
        db,
        event_hub,
        model_runner,
    ):
        self.db = db
        self.event_hub = event_hub
        self.model_runner = model_runner
        self.worker_lease_id = str(uuid.uuid4())
        self.running_inference: Dict[str, asyncio.Event] = {}

    async def run(self):
        """Main worker loop: poll → lease → run inference → finalize."""
        print(f"🚀 CommunityInferenceWorker started (lease_id={self.worker_lease_id[:8]})")
        
        while True:
            try:
                # Atomically lease one task
                task = await self._lease_inference()
                
                if not task:
                    await asyncio.sleep(self.POLL_INTERVAL_SEC)
                    continue

                task_id = task["task_id"]
                model_id = task["model_id"]
                
                print(f"▶️  InferenceWorker: starting {task_id[:8]}")
                
                # Parse inputs
                try:
                    prompt_json = json.loads(task["prompt"])
                    messages = prompt_json.get("messages", [])
                    parameters = json.loads(task["parameters"])
                except json.JSONDecodeError as e:
                    await self._finalize_inference(
                        task_id,
                        status="FAILED",
                        error_log=f"JSON parse error: {str(e)}"
                    )
                    continue
                
                # Create cancel event
                cancel_event = asyncio.Event()
                self.running_inference[task_id] = cancel_event

                try:
                    # Ensure model loaded
                    await self.model_runner.ensure_loaded(model_id)

                    # Stream tokens with callback
                    async def on_token(token: str):
                        await self.event_hub.publish(
                            f"inference:{task_id}",
                            {
                                "type": "TOKEN",
                                "task_id": task_id,
                                "data": {"text": token},
                                "ts": int(datetime.utcnow().timestamp()),
                            }
                        )

                    # Run inference
                    result_json, tokens_per_second = await self.model_runner.run_chat(
                        messages=messages,
                        parameters=parameters,
                        on_token=on_token,
                        cancel_event=cancel_event,
                    )

                    # Finalize: SUCCESS
                    await self._finalize_inference(
                        task_id,
                        status="COMPLETED",
                        result=result_json,
                        tokens_per_second=tokens_per_second,
                    )
                    
                    # Publish DONE event
                    await self.event_hub.publish(
                        f"inference:{task_id}",
                        {
                            "type": "DONE",
                            "task_id": task_id,
                            "data": {
                                "result": result_json,
                                "tokens_per_second": tokens_per_second,
                            },
                            "ts": int(datetime.utcnow().timestamp()),
                        }
                    )

                except asyncio.CancelledError:
                    await self._finalize_inference(task_id, status="CANCELED")
                    
                    await self.event_hub.publish(
                        f"inference:{task_id}",
                        {
                            "type": "CANCELED",
                            "task_id": task_id,
                            "ts": int(datetime.utcnow().timestamp()),
                        }
                    )

                except Exception as e:
                    error_log = traceback.format_exc()
                    await self._finalize_inference(
                        task_id,
                        status="FAILED",
                        error_log=error_log,
                    )
                    
                    await self.event_hub.publish(
                        f"inference:{task_id}",
                        {
                            "type": "ERROR",
                            "task_id": task_id,
                            "data": {
                                "message": str(e),
                                "trace": error_log,
                            },
                            "ts": int(datetime.utcnow().timestamp()),
                        }
                    )

                finally:
                    self.running_inference.pop(task_id, None)

            except Exception as e:
                print(f"❌ InferenceWorker error: {e}")
                await asyncio.sleep(self.POLL_INTERVAL_SEC)

    async def _lease_inference(self) -> Optional[Dict]:
        """Atomically lease one inference task (CRITICAL: single SQL statement)"""
        query = """
            UPDATE inference_queue
            SET
                status = 'RUNNING',
                lease_id = :lease_id,
                lease_expires_at = CAST(strftime('%s', 'now') AS INTEGER) + :lease_ttl,
                started_at = COALESCE(started_at, CAST(strftime('%s', 'now') AS INTEGER))
            WHERE task_id = (
                SELECT task_id
                FROM inference_queue
                WHERE status = 'PENDING'
                ORDER BY priority DESC, enqueue_ts ASC
                LIMIT 1
            )
            RETURNING task_id, model_id, prompt, parameters, priority
        """
        return self.db.execute_returning(query, {
            "lease_id": self.worker_lease_id,
            "lease_ttl": self.LEASE_TTL_SEC,
        })

    async def _finalize_inference(
        self,
        task_id: str,
        status: str,
        result: Optional[dict] = None,
        tokens_per_second: Optional[float] = None,
        error_log: Optional[str] = None,
    ):
        """Write final status to DB."""
        now_ts = int(datetime.utcnow().timestamp())
        
        query = """
            UPDATE inference_queue
            SET
                status = :status,
                completed_at = :completed_at,
                result = :result,
                tokens_per_second = :tokens_per_second,
                error_log = :error_log
            WHERE task_id = :task_id
        """
        self.db.execute_update(query, {
            "task_id": task_id,
            "status": status,
            "completed_at": now_ts,
            "result": json.dumps(result) if result else None,
            "tokens_per_second": tokens_per_second,
            "error_log": error_log,
        })
        
        print(f"✅ InferenceWorker: {task_id[:8]} → {status}")

    async def cancel_inference(self, task_id: str):
        """Cancel running inference."""
        if task_id in self.running_inference:
            self.running_inference[task_id].set()
            print(f"⛔ InferenceWorker: cancel requested for {task_id[:8]}")
