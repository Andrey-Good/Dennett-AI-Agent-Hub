# dennett/core/enqueue.py
"""
EnqueueService: Queue executions and inference tasks with priority assignment.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

class EnqueueService:
    """Service for enqueueing tasks with priority management."""
    
    def __init__(self, db, priority_policy):
        self.db = db
        self.priority_policy = priority_policy

    def enqueue_execution(
        self,
        agent_id: str,
        payload: dict,
        source: str = "MANUAL_RUN",
        parent_execution_id: Optional[str] = None,
        parent_priority: Optional[int] = None,
    ) -> str:
        """
        Enqueue execution: creates execution_id, inserts into executions,
        records input_start event with payload.
        Returns execution_id (UUIDv7).
        """
        execution_id = str(uuid.uuid4())
        now_ts = int(datetime.utcnow().timestamp())
        
        # Assign priority
        priority = self.priority_policy.assign_priority(
            source,
            parent_priority=parent_priority
        )
        base_priority = self.priority_policy.assign_priority(source)

        with self.db.transaction():
            # 1. Create execution record
            query = """
                INSERT INTO executions (
                    execution_id, agent_id, status,
                    parent_execution_id, base_priority, priority,
                    enqueue_ts, created_at
                )
                VALUES (:execution_id, :agent_id, 'PENDING',
                        :parent_execution_id, :base_priority, :priority,
                        :enqueue_ts, :created_at)
            """
            self.db.execute_update(query, {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "parent_execution_id": parent_execution_id,
                "base_priority": base_priority,
                "priority": priority,
                "enqueue_ts": now_ts,
                "created_at": now_ts,
            })

            # 2. Record input_start event (so graph can read node:input_start.*)
            query = """
                INSERT INTO node_events (
                    execution_id, node_id, status,
                    intermediate_output, started_at, completed_at
                )
                VALUES (:execution_id, 'input_start', 'COMPLETED',
                        :intermediate_output, :started_at, :completed_at)
            """
            self.db.execute_update(query, {
                "execution_id": execution_id,
                "intermediate_output": json.dumps(payload),
                "started_at": now_ts,
                "completed_at": now_ts,
            })

        print(f"📝 Enqueued execution: {execution_id[:8]} (priority={priority})")
        return execution_id

    def enqueue_inference(
        self,
        model_id: str,
        messages: list,
        parameters: dict,
        source: str = "CHAT",
        parent_priority: Optional[int] = None,
    ) -> str:
        """
        Enqueue inference task into queue.
        Returns task_id (UUIDv7).
        """
        task_id = str(uuid.uuid4())
        now_ts = int(datetime.utcnow().timestamp())
        
        # Assign priority
        priority = self.priority_policy.assign_priority(
            source,
            parent_priority=parent_priority
        )
        base_priority = self.priority_policy.assign_priority(source)

        query = """
            INSERT INTO inference_queue (
                task_id, model_id, status,
                prompt, parameters,
                base_priority, priority,
                enqueue_ts, created_at
            )
            VALUES (:task_id, :model_id, 'PENDING',
                    :prompt, :parameters,
                    :base_priority, :priority,
                    :enqueue_ts, :created_at)
        """
        self.db.execute_update(query, {
            "task_id": task_id,
            "model_id": model_id,
            "prompt": json.dumps({"messages": messages}),
            "parameters": json.dumps(parameters),
            "base_priority": base_priority,
            "priority": priority,
            "enqueue_ts": now_ts,
            "created_at": now_ts,
        })

        print(f"📝 Enqueued inference: {task_id[:8]} (priority={priority})")
        return task_id
