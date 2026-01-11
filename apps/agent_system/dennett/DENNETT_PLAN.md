# Dennett AI Core v5.0 Community - Full Implementation Plan

**Status:** Implementation-ready  
**Date:** 2025-12-24

---

## 📋 OVERVIEW

Это ядро локальной службы с двумя очередями (агенты + инференс), двумя воркерами, приоритетами, надежностью и realtime потоком.

**Архитектура в одном предложении:**
```
UI/Триггер → API (enqueue) → SQLite очереди → AgentWorker / InferenceWorker → ModelRunner / AgentExecutor → SQLite результаты + EventHub/WS
```

---

## 🎯 COMPONENTS TO BUILD

### Tier 1: Database & Core Infrastructure
1. **SQLite Schema** (storage.db)
   - Таблицы: executions, inference_queue, node_events
   - Индексы, PRAGMA, WAL
   - Status constants

2. **DBInterface** (compatibility layer)
   - Abstraction для работы с SQLite
   - Методы: SELECT, INSERT, UPDATE (atomic lease)

3. **PriorityPolicy** (scheduling logic)
   - assign_priority()
   - run_aging_worker() (anti-starvation)

### Tier 2: Queue Management
4. **Enqueue Service**
   - enqueue_execution()
   - enqueue_inference()

5. **StartupRecovery**
   - На старте вернуть RUNNING → PENDING

### Tier 3: Workers
6. **AgentWorker**
   - Цикл: lease → run AgentExecutor → finalize

7. **CommunityInferenceWorker**
   - Цикл: lease → run ModelRunner → stream tokens → finalize

### Tier 4: Realtime & API
8. **EventHub** (in-process pub/sub)
   - Channel: execution:{id}, inference:{id}

9. **HTTP/WS API**
   - REST endpoints
   - WebSocket for streaming

### Tier 5: Compatibility
10. **ModelRunner** (refactor boundaries)
11. **AgentExecutor** (add run_graph() alias)

---

## 🏗️ IMPLEMENTATION DETAIL

### 1. SQLite Schema & Config

**File: `core/db.py`**

```python
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import json
import uuid
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, db_path: str = "storage.db"):
        self.db_path = db_path
        self.local = threading.local()
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Thread-local SQLite connection."""
        if not hasattr(self.local, "conn"):
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.row_factory = sqlite3.Row
            self._apply_pragmas(self.local.conn)
        return self.local.conn

    def _apply_pragmas(self, conn: sqlite3.Connection):
        """Applies required PRAGMA settings."""
        pragmas = [
            "PRAGMA journal_mode=WAL;",
            "PRAGMA busy_timeout=5000;",
            "PRAGMA wal_autocheckpoint=1000;",
            "PRAGMA synchronous=NORMAL;",
        ]
        for pragma in pragmas:
            conn.execute(pragma)
        conn.commit()

    def _ensure_schema(self):
        """Create tables if not exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # === executions table ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                execution_id        TEXT PRIMARY KEY,
                agent_id            TEXT NOT NULL,
                status              TEXT NOT NULL,
                parent_execution_id TEXT,
                final_result        TEXT,
                base_priority       INTEGER NOT NULL,
                priority            INTEGER NOT NULL,
                enqueue_ts          INTEGER NOT NULL,
                boost_expires_at    INTEGER,
                lease_id            TEXT,
                lease_expires_at    INTEGER,
                created_at          INTEGER NOT NULL DEFAULT (unixepoch()),
                started_at          INTEGER,
                completed_at        INTEGER,
                error_log           TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_executions_queue
            ON executions (status, priority DESC, enqueue_ts ASC)
        """)

        # === inference_queue table ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inference_queue (
                task_id            TEXT PRIMARY KEY,
                model_id           TEXT NOT NULL,
                status             TEXT NOT NULL,
                prompt             TEXT NOT NULL,
                parameters         TEXT NOT NULL,
                result             TEXT,
                base_priority      INTEGER NOT NULL,
                priority           INTEGER NOT NULL,
                enqueue_ts         INTEGER NOT NULL,
                boost_expires_at   INTEGER,
                lease_id           TEXT,
                lease_expires_at   INTEGER,
                created_at         INTEGER NOT NULL DEFAULT (unixepoch()),
                started_at         INTEGER,
                completed_at       INTEGER,
                tokens_per_second  REAL,
                error_log          TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_inference_queue
            ON inference_queue (status, priority DESC, enqueue_ts ASC)
        """)

        # === node_events table ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_events (
                event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id        TEXT NOT NULL,
                node_id             TEXT NOT NULL,
                status              TEXT NOT NULL,
                intermediate_output TEXT,
                started_at          INTEGER,
                completed_at        INTEGER,
                error_log           TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_node_events_exec
            ON node_events (execution_id, event_id)
        """)

        conn.commit()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute SELECT query, return first row."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        row = cursor.fetchone()
        return dict(row) if row else None

    def execute_update(self, query: str, params: Optional[Dict] = None) -> int:
        """Execute INSERT/UPDATE/DELETE, return row count."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        conn.commit()
        return cursor.rowcount

    def execute_returning(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute statement with RETURNING, return first row."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        conn.commit()
        row = cursor.fetchone()
        return dict(row) if row else None

    def transaction(self):
        """Context manager for transactions."""
        class _Transaction:
            def __init__(self, db):
                self.db = db
            def __enter__(self):
                self.db._get_connection().execute("BEGIN")
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.db._get_connection().rollback()
                else:
                    self.db._get_connection().commit()
        return _Transaction(self)
```

---

### 2. Priority Policy

**File: `core/priority.py`**

```python
import asyncio
from datetime import datetime, timedelta
from core.db import DatabaseManager

class PriorityPolicy:
    # Base priorities (коридоры источников)
    PRIORITY_CHAT = 90
    PRIORITY_MANUAL_RUN = 70
    PRIORITY_INTERNAL_NODE = 50
    PRIORITY_TRIGGER = 30

    # Anti-starvation
    AGING_INTERVAL_SEC = 60
    AGING_THRESHOLD_SEC = 300
    AGING_BOOST = 10
    AGING_CAP_COMMUNITY = 65

    def __init__(self, db: DatabaseManager):
        self.db = db

    def assign_priority(
        self,
        source: str,  # "CHAT" | "MANUAL_RUN" | "INTERNAL_NODE" | "TRIGGER"
        parent_priority: Optional[int] = None,
        agent_config: Optional[dict] = None
    ) -> int:
        """
        Assign priority: max(base_priority_from_source, parent_priority)
        """
        base_map = {
            "CHAT": self.PRIORITY_CHAT,
            "MANUAL_RUN": self.PRIORITY_MANUAL_RUN,
            "INTERNAL_NODE": self.PRIORITY_INTERNAL_NODE,
            "TRIGGER": self.PRIORITY_TRIGGER,
        }
        base = base_map.get(source, self.PRIORITY_TRIGGER)
        
        if parent_priority is not None:
            return max(base, parent_priority)
        return base

    async def run_aging_worker(self, db_session: DatabaseManager):
        """
        Фоновый цикл: каждые 60 сек проверяет задачи в очереди > 300 сек
        и повышает их приоритет на +10 (до 65 в Community).
        """
        while True:
            try:
                await asyncio.sleep(self.AGING_INTERVAL_SEC)
                
                now_ts = int(datetime.utcnow().timestamp())
                threshold_ts = now_ts - self.AGING_THRESHOLD_SEC

                # Обновляем executions
                query = """
                    UPDATE executions
                    SET priority = MIN(priority + ?, ?)
                    WHERE status = 'PENDING'
                      AND enqueue_ts < ?
                """
                db_session.execute_update(
                    query,
                    {
                        "boost": self.AGING_BOOST,
                        "cap": self.AGING_CAP_COMMUNITY,
                        "threshold": threshold_ts,
                    }
                )

                # Обновляем inference_queue
                query = """
                    UPDATE inference_queue
                    SET priority = MIN(priority + ?, ?)
                    WHERE status = 'PENDING'
                      AND enqueue_ts < ?
                """
                db_session.execute_update(
                    query,
                    {
                        "boost": self.AGING_BOOST,
                        "cap": self.AGING_CAP_COMMUNITY,
                        "threshold": threshold_ts,
                    }
                )
            except Exception as e:
                print(f"❌ AgingWorker error: {e}")
```

---

### 3. Enqueue Service

**File: `core/enqueue.py`**

```python
import json
import uuid
from datetime import datetime
from core.db import DatabaseManager
from core.priority import PriorityPolicy

class EnqueueService:
    def __init__(self, db: DatabaseManager, priority_policy: PriorityPolicy):
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
        Поставить execution в очередь.
        Возвращает execution_id (UUIDv7).
        
        В транзакции:
        1. INSERT INTO executions (PENDING)
        2. INSERT INTO node_events (input_start with payload)
        """
        execution_id = str(uuid.uuid7())
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

            # 2. Record input_start event
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

        return execution_id

    def enqueue_inference(
        self,
        model_id: str,
        messages: list[dict],
        parameters: dict,
        source: str = "CHAT",
        parent_priority: Optional[int] = None,
    ) -> str:
        """
        Поставить inference задачу в очередь.
        Возвращает task_id (UUIDv7).
        """
        task_id = str(uuid.uuid7())
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

        return task_id
```

---

### 4. Startup Recovery

**File: `core/recovery.py`**

```python
from core.db import DatabaseManager

class StartupRecovery:
    @staticmethod
    def recover(db: DatabaseManager):
        """
        На старте: возвращаем RUNNING и CANCEL_REQUESTED обратно в PENDING.
        """
        # Recover executions
        query = """
            UPDATE executions
            SET status = 'PENDING', lease_id = NULL, lease_expires_at = NULL
            WHERE status IN ('RUNNING', 'CANCEL_REQUESTED')
        """
        db.execute_update(query)

        # Recover inference_queue
        query = """
            UPDATE inference_queue
            SET status = 'PENDING', lease_id = NULL, lease_expires_at = NULL
            WHERE status IN ('RUNNING', 'CANCEL_REQUESTED')
        """
        db.execute_update(query)

        print("✓ StartupRecovery: RUNNING/CANCEL_REQUESTED → PENDING")
```

---

### 5. EventHub (in-process pub/sub)

**File: `core/eventhub.py`**

```python
import asyncio
from typing import Callable, Dict, List, Any
from datetime import datetime

class EventHub:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.lock = asyncio.Lock()

    def subscribe(self, channel: str, callback: Callable[[Dict], None]):
        """Subscribe to channel: execution:{id}, inference:{id}"""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)

    async def publish(self, channel: str, event: Dict[str, Any]):
        """Publish event to channel."""
        async with self.lock:
            if channel in self.subscribers:
                for callback in self.subscribers[channel]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        print(f"❌ EventHub callback error: {e}")

    def unsubscribe(self, channel: str, callback: Callable):
        """Unsubscribe from channel."""
        if channel in self.subscribers:
            self.subscribers[channel].remove(callback)
```

---

### 6. AgentWorker

**File: `core/workers/agent_worker.py`**

```python
import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Optional
from core.db import DatabaseManager
from core.eventhub import EventHub

class AgentWorker:
    LEASE_TTL_SEC = 600
    POLL_INTERVAL_SEC = 0.1

    def __init__(
        self,
        db: DatabaseManager,
        event_hub: EventHub,
        agent_executor_class,  # AgentExecutor class
        node_registry,
    ):
        self.db = db
        self.event_hub = event_hub
        self.agent_executor_class = agent_executor_class
        self.node_registry = node_registry
        self.worker_lease_id = str(uuid.uuid4())
        self.running_executions: Dict[str, asyncio.Event] = {}

    async def run(self):
        """Main worker loop."""
        print(f"🚀 AgentWorker started (lease_id={self.worker_lease_id[:8]})")
        
        while True:
            try:
                # Lease one execution atomically
                task = await self._lease_execution()
                
                if not task:
                    await asyncio.sleep(self.POLL_INTERVAL_SEC)
                    continue

                execution_id = task["execution_id"]
                agent_id = task["agent_id"]
                
                print(f"▶️  AgentWorker: starting execution {execution_id[:8]}")
                
                # Create cancel event
                cancel_event = asyncio.Event()
                self.running_executions[execution_id] = cancel_event

                try:
                    # Load agent config (from file or DB)
                    agent_config = self._load_agent_config(agent_id)

                    # Create AgentExecutor instance
                    executor = self.agent_executor_class(
                        agent_config=agent_config,
                        execution_id=execution_id,
                        db_session=self.db,
                        registry=self.node_registry,
                        event_emitter=self._emit_node_event,
                        cancellation_token=cancel_event,
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
                    # Finalize: CANCELED
                    await self._finalize_execution(
                        execution_id,
                        status="CANCELED"
                    )
                    
                except Exception as e:
                    # Finalize: FAILED
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
        """Atomically lease one execution: UPDATE...RETURNING"""
        query = """
            UPDATE executions
            SET
                status = 'RUNNING',
                lease_id = :lease_id,
                lease_expires_at = unixepoch() + :lease_ttl,
                started_at = COALESCE(started_at, unixepoch())
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
        """Callback для AgentExecutor когда нода завершилась."""
        await self.event_hub.publish(
            f"execution:{event['execution_id']}",
            event
        )

    def _load_agent_config(self, agent_id: str) -> Dict:
        """Load agent config from file or DB."""
        # TODO: implement based on your agents storage
        return {}

    async def cancel_execution(self, execution_id: str):
        """Cancel running execution."""
        if execution_id in self.running_executions:
            self.running_executions[execution_id].set()
```

---

### 7. CommunityInferenceWorker

**File: `core/workers/inference_worker.py`**

```python
import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Optional
from core.db import DatabaseManager
from core.eventhub import EventHub

class CommunityInferenceWorker:
    LEASE_TTL_SEC = 300
    POLL_INTERVAL_SEC = 0.1

    def __init__(
        self,
        db: DatabaseManager,
        event_hub: EventHub,
        model_runner,  # ModelRunner instance
    ):
        self.db = db
        self.event_hub = event_hub
        self.model_runner = model_runner
        self.worker_lease_id = str(uuid.uuid4())
        self.running_inference: Dict[str, asyncio.Event] = {}

    async def run(self):
        """Main worker loop."""
        print(f"🚀 CommunityInferenceWorker started (lease_id={self.worker_lease_id[:8]})")
        
        while True:
            try:
                # Lease one task atomically
                task = await self._lease_inference()
                
                if not task:
                    await asyncio.sleep(self.POLL_INTERVAL_SEC)
                    continue

                task_id = task["task_id"]
                model_id = task["model_id"]
                
                print(f"▶️  InferenceWorker: starting task {task_id[:8]}")
                
                # Parse inputs
                prompt_json = json.loads(task["prompt"])
                messages = prompt_json.get("messages", [])
                parameters = json.loads(task["parameters"])
                
                # Create cancel event
                cancel_event = asyncio.Event()
                self.running_inference[task_id] = cancel_event

                try:
                    # Ensure model loaded
                    await self.model_runner.ensure_loaded(model_id)

                    # Stream tokens with callback
                    tokens = []
                    
                    async def on_token(token: str):
                        tokens.append(token)
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
                    # Finalize: CANCELED
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
                    # Finalize: FAILED
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
        """Atomically lease one inference task."""
        query = """
            UPDATE inference_queue
            SET
                status = 'RUNNING',
                lease_id = :lease_id,
                lease_expires_at = unixepoch() + :lease_ttl,
                started_at = COALESCE(started_at, unixepoch())
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
```

---

### 8. REST API + WebSocket

**File: `api/server.py`**

```python
import asyncio
import json
from fastapi import FastAPI, WebSocket, HTTPException
from datetime import datetime
from core.db import DatabaseManager
from core.enqueue import EnqueueService
from core.recovery import StartupRecovery
from core.eventhub import EventHub
from core.priority import PriorityPolicy

app = FastAPI(title="Dennett AI Core v5.0", version="5.0")

# Global state
db: DatabaseManager = None
enqueue: EnqueueService = None
event_hub: EventHub = None
agent_worker = None
inference_worker = None
startup_ts = datetime.utcnow().timestamp()

@app.on_event("startup")
async def startup():
    global db, enqueue, event_hub, agent_worker, inference_worker, startup_ts
    
    startup_ts = datetime.utcnow().timestamp()
    db = DatabaseManager()
    event_hub = EventHub()
    priority_policy = PriorityPolicy(db)
    enqueue = EnqueueService(db, priority_policy)
    
    # Recover from crash
    StartupRecovery.recover(db)
    
    # Start aging worker
    asyncio.create_task(priority_policy.run_aging_worker(db))
    
    # TODO: Start AgentWorker and InferenceWorker
    
    print("✅ Core started")

# === REST ENDPOINTS ===

@app.post("/executions/run")
async def run_execution(payload: dict):
    """POST /executions/run - start agent execution"""
    execution_id = enqueue.enqueue_execution(
        agent_id=payload.get("agent_id"),
        payload=payload.get("input", {}),
        source="MANUAL_RUN",
    )
    return {
        "execution_id": execution_id,
        "status": "QUEUED",
    }

@app.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """GET /executions/{id} - get execution status"""
    query = "SELECT * FROM executions WHERE execution_id = ?"
    row = db.execute_query(query, {"execution_id": execution_id})
    
    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return dict(row)

@app.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """POST /executions/{id}/cancel - cancel execution"""
    # Set status to CANCEL_REQUESTED
    query = """
        UPDATE executions
        SET status = 'CANCEL_REQUESTED'
        WHERE execution_id = ?
    """
    db.execute_update(query, {"execution_id": execution_id})
    
    # Signal cancel event to worker if running
    # TODO: agent_worker.cancel_execution(execution_id)
    
    return {"status": "cancel_requested"}

@app.post("/inference/chat")
async def chat_inference(payload: dict):
    """POST /inference/chat - start inference task"""
    task_id = enqueue.enqueue_inference(
        model_id=payload.get("model_id"),
        messages=payload.get("messages", []),
        parameters=payload.get("parameters", {}),
        source="CHAT",
    )
    return {
        "task_id": task_id,
        "status": "QUEUED",
    }

@app.get("/inference/{task_id}")
async def get_inference(task_id: str):
    """GET /inference/{task_id} - get inference status"""
    query = "SELECT * FROM inference_queue WHERE task_id = ?"
    row = db.execute_query(query, {"task_id": task_id})
    
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return dict(row)

@app.post("/inference/{task_id}/cancel")
async def cancel_inference(task_id: str):
    """POST /inference/{task_id}/cancel - cancel inference"""
    query = """
        UPDATE inference_queue
        SET status = 'CANCEL_REQUESTED'
        WHERE task_id = ?
    """
    db.execute_update(query, {"task_id": task_id})
    
    # TODO: inference_worker.cancel_inference(task_id)
    
    return {"status": "cancel_requested"}

@app.websocket("/inference/{task_id}/stream")
async def websocket_inference_stream(websocket: WebSocket, task_id: str):
    """WS /inference/{task_id}/stream - stream inference tokens"""
    await websocket.accept()
    
    # Check task exists
    query = "SELECT status FROM inference_queue WHERE task_id = ?"
    task = db.execute_query(query, {"task_id": task_id})
    
    if not task:
        await websocket.close(code=4004, reason="Task not found")
        return
    
    # Subscribe to event channel
    async def on_event(event: dict):
        await websocket.send_json(event)
    
    event_hub.subscribe(f"inference:{task_id}", on_event)
    
    try:
        while True:
            # Keep connection open
            await asyncio.sleep(1)
    finally:
        event_hub.unsubscribe(f"inference:{task_id}", on_event)

@app.get("/admin/health")
async def health():
    """GET /admin/health - health check"""
    uptime_sec = int(datetime.utcnow().timestamp() - startup_ts)
    
    # Get SQLite version
    version_row = db.execute_query("SELECT sqlite_version() as version")
    sqlite_version = version_row["version"] if version_row else "unknown"
    
    return {
        "status": "ok",
        "sqlite_version": sqlite_version,
        "uptime_sec": uptime_sec,
    }
```

---

## 📊 INTEGRATION CHECKLIST

Before Delivery:

- [ ] **Database**
  - [ ] SQLite with WAL + PRAGMA
  - [ ] All 3 tables created with indices
  - [ ] Status constants defined

- [ ] **Priority & Queuing**
  - [ ] PriorityPolicy.assign_priority() works
  - [ ] AgingWorker increases priority correctly
  - [ ] Gatekeeper: all enqueue goes through PriorityPolicy

- [ ] **Leasing (CRITICAL)**
  - [ ] UPDATE…RETURNING is single SQL statement
  - [ ] Test: 2 workers, 20 tasks → no duplicates
  - [ ] Logs show exactly 1 SELECT per task taken

- [ ] **Workers**
  - [ ] AgentWorker: cycles, leases, executes, finalizes
  - [ ] InferenceWorker: cycles, leases, runs ModelRunner, streams, finalizes
  - [ ] Both handle cancel gracefully

- [ ] **Reliability**
  - [ ] Kill -9 test: RUNNING → PENDING → recovered
  - [ ] Aging: PENDING > 300s → priority increases
  - [ ] EventHub publishes correctly

- [ ] **API**
  - [ ] /executions/run → enqueues
  - [ ] /executions/{id} → reads status
  - [ ] /inference/chat → enqueues
  - [ ] WS /inference/{id}/stream → TOKEN/DONE/ERROR flow

- [ ] **Contracts**
  - [ ] AgentExecutor has run_graph() alias/method
  - [ ] ModelRunner matches contract (ensure_loaded, run_chat, cancel)
  - [ ] JSON formats match spec (prompt, result, etc.)

---

## 🔍 Kill-9 Recovery Test

```bash
# Terminal 1
python -m api.server

# Terminal 2
# POST /executions/run → get execution_id
curl -X POST http://localhost:8000/executions/run \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"test","input":{}}'

# Kill process (kill -9 <PID>)
# Restart
python -m api.server

# Check: status should be PENDING (not RUNNING)
curl http://localhost:8000/executions/<execution_id>

# Should show: "status": "PENDING"
```

---

**This is your full implementation roadmap. Start with DB + PriorityPolicy, then workers, then API.**
