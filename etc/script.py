from __future__ import annotations

import asyncio
import heapq
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    from llama_cpp import Llama
    REAL_LLAMA = True
except Exception:
    REAL_LLAMA = False

try:
    from starlette.responses import EventSourceResponse
except Exception:
    EventSourceResponse = None

try:
    import pynvml
    PYNVML_AVAILABLE = True
except Exception:
    PYNVML_AVAILABLE = False

try:
    import amdgpuinfo
    AMDGPU_AVAILABLE = True
except Exception:
    AMDGPU_AVAILABLE = False

DEFAULT_CONFIG = {
    "db_path": "inference_queue.db",
    "max_vram_mb": 12288,
    "worker_count": 2,
    "model_vram_estimates": {
        "llama3-8b-instruct.Q4_K_M.gguf": 8192,
        "llama2-7b.gguf": 6144,
    },
    "logging": {"level": "INFO"},
    "gpu_vendor": "auto",
    "gpu_monitor_interval_sec": 10,
    "queue": {
        "cleanup_ttl_days": 7,
        "max_history_size": 10000
    },
    "gpus": []
}

CONFIG_PATH = Path("config.yaml")

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        detail = getattr(record, "detail", None)
        if detail is not None:
            obj["detail"] = detail
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, ensure_ascii=False)

logger = logging.getLogger("inference_service")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def deep_update(base: Dict, updates: Dict) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value

def load_config() -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f)
            if user_cfg:
                deep_update(cfg, user_cfg)
        except Exception as e:
            logger.warning("Failed to read config.yaml", extra={"detail": str(e)})
    logger.info("Configuration loaded")
    return cfg

CONFIG = load_config()
logger.setLevel(getattr(logging, CONFIG.get("logging", {}).get("level", "INFO")))

DB_SCHEMA_VERSION = 1

CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT,
    priority INTEGER,
    model_id TEXT,
    model_params_json TEXT,
    input_data_json TEXT,
    params_json TEXT,
    result_json TEXT,
    error_text TEXT,
    created_at DATETIME,
    updated_at DATETIME
)
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)
"""

async def init_db(db_path: str):
    logger.info("Initializing DB", extra={"detail": db_path})
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute(CREATE_TASKS_TABLE)
        await db.execute(CREATE_INDEXES)
        
        cur = await db.execute("PRAGMA user_version")
        row = await cur.fetchone()
        current_version = row[0] if row else 0
        
        if current_version < DB_SCHEMA_VERSION:
            logger.info("Applying DB schema version change", 
                       extra={"detail": f"{current_version} -> {DB_SCHEMA_VERSION}"})
            await db.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION}")
            await db.commit()

class MockModel:
    def __init__(self, model_path: str, n_ctx: int = 2048, n_gpu_layers: int = -1):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers

    def generate_stream(self, prompt: str, temperature: float = 0.7):
        words = f"Mock response to: {prompt}".split()
        for w in words:
            time.sleep(0.05)
            yield w

    def generate(self, prompt: str, temperature: float = 0.7):
        return " ".join(list(self.generate_stream(prompt, temperature)))

class ModelLoadError(Exception):
    pass

class ModelInstance:
    def __init__(self, model_id: str, model_path: str, n_ctx: int = 2048,
                 n_gpu_layers: int = -1, estimated_vram_mb: int = 4096):
        self.model_id = model_id
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.status = "initialized"
        self.last_used = time.time()
        self.estimated_vram_mb = estimated_vram_mb
        self.actual_vram_mb = 0
        self.model = None
        self.lock = asyncio.Lock()
        self.assigned_gpu: Optional[int] = None

    async def load(self, assign_gpu: Optional[int] = None):
        async with self.lock:
            if self.status in ["ready", "loading"]:
                return
            
            self.status = "loading"
            self.assigned_gpu = assign_gpu
            
            logger.info(f"Loading model {self.model_id}", 
                       extra={"detail": {
                           "n_gpu_layers": self.n_gpu_layers,
                           "n_ctx": self.n_ctx,
                           "gpu": assign_gpu
                       }})
            
            try:
                if REAL_LLAMA:
                    self.model = Llama(
                        model_path=self.model_path,
                        n_ctx=self.n_ctx,
                        n_gpu_layers=self.n_gpu_layers
                    )
                else:
                    await asyncio.sleep(0.2)
                    self.model = MockModel(self.model_path, self.n_ctx, self.n_gpu_layers)
                
                self.actual_vram_mb = self.estimated_vram_mb
                self.status = "ready"
                self.touch()
                
                logger.info(f"Model {self.model_id} loaded", 
                           extra={"detail": {"vram_mb": self.actual_vram_mb}})
            except Exception as e:
                self.status = "failed"
                logger.error(f"Failed to load model {self.model_id}", 
                           extra={"detail": str(e)})
                raise ModelLoadError(str(e))

    async def unload(self):
        async with self.lock:
            if self.status == "unloading":
                return
            
            logger.info(f"Unloading model {self.model_id}")
            self.status = "unloading"
            
            try:
                if self.model and REAL_LLAMA:
                    del self.model
                self.model = None
                await asyncio.sleep(0.05)
            finally:
                self.status = "unloaded"
            
            logger.info(f"Model {self.model_id} unloaded")

    def touch(self):
        self.last_used = time.time()

    async def infer(self, input_data: Dict[str, Any], params: Dict[str, Any],
                   stream_queue: Optional[asyncio.Queue] = None,
                   cancel_event: Optional[asyncio.Event] = None) -> Dict[str, Any]:
        async with self.lock:
            if self.status != "ready":
                raise RuntimeError(f"Model {self.model_id} not ready (status={self.status})")
            
            self.touch()
            input_type = input_data.get("type", "text")
            temperature = params.get("temperature", 0.7)
            
            if input_type == "image":
                b64 = input_data.get("content")
                mime = input_data.get("mime", "image/png")
                prompt_text = input_data.get("prompt", "")
                data_uri = f"data:{mime};base64,{b64}"
                prompt = f"{prompt_text} [IMAGE: {data_uri[:50]}...]"
            else:
                prompt = input_data.get("content", "")
            
            if stream_queue is not None:
                logger.info(f"Starting streaming inference on {self.model_id}")
                try:
                    for token in self.model.generate_stream(prompt, temperature):
                        if cancel_event and cancel_event.is_set():
                            raise asyncio.CancelledError("Task cancelled")
                        await stream_queue.put({"token": token})
                    
                    await stream_queue.put({"event": "done"})
                    return {"type": "text", "content": ""}
                except asyncio.CancelledError:
                    logger.info("Streaming inference cancelled")
                    await stream_queue.put({"event": "error", "error": "Cancelled"})
                    raise
                except Exception as e:
                    logger.error(f"Streaming inference failed: {e}")
                    await stream_queue.put({"event": "error", "error": str(e)})
                    raise
            else:
                logger.info(f"Starting batch inference on {self.model_id}")
                output = self.model.generate(prompt, temperature)
                return {"type": "text", "content": output}


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    seq: int
    task_id: str = field(compare=False)

class GPUInfo:
    def __init__(self, id: int, vendor: str, max_utilization: int,
                 max_memory_mb: int, allow_models: Optional[List[str]] = None):
        self.id = id
        self.vendor = vendor
        self.max_utilization = max_utilization
        self.max_memory_mb = max_memory_mb
        self.allow_models = allow_models or []
        self.last_free_mb = max_memory_mb
        self.used_mb = 0

class GPUManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gpus: Dict[int, GPUInfo] = {}
        self.cpu_fallback = False
        self.monitor_interval = int(config.get("gpu_monitor_interval_sec", 10))
        self.monitor_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    def init_gpus(self):
        cfg_gpus = self.config.get("gpus", [])
        
        if cfg_gpus:
            for g in cfg_gpus:
                info = GPUInfo(
                    id=g["id"],
                    vendor=g.get("vendor", "auto"),
                    max_utilization=g.get("max_utilization", 90),
                    max_memory_mb=g.get("max_memory_mb", 16000),
                    allow_models=g.get("allow_models", [])
                )
                self.gpus[info.id] = info
        else:
            if PYNVML_AVAILABLE:
                try:
                    pynvml.nvmlInit()
                    device_count = pynvml.nvmlDeviceGetCount()
                    for i in range(device_count):
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        max_mb = int(mem.total / 1024 / 1024)
                        self.gpus[i] = GPUInfo(i, "nvidia", 90, max_mb)
                except Exception as e:
                    logger.warning("pynvml init failed", extra={"detail": str(e)})
            elif AMDGPU_AVAILABLE:
                try:
                    cards = amdgpuinfo.get_info()
                    for idx, c in enumerate(cards):
                        max_mb = c.get("vram_total", 0)
                        self.gpus[idx] = GPUInfo(idx, "amd", 80, max_mb)
                except Exception as e:
                    logger.warning("amdgpuinfo init failed", extra={"detail": str(e)})
            else:
                logger.warning("No GPU detection available; CPU fallback")
                self.cpu_fallback = True

    async def start_monitor(self):
        if self.cpu_fallback or not self.gpus:
            return
        if self.monitor_task:
            return
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitor(self):
        if self.monitor_task:
            self.monitor_task.cancel()
            await asyncio.gather(self.monitor_task, return_exceptions=True)

    async def _monitor_loop(self):
        while True:
            try:
                await self.update_gpu_stats()
            except Exception as e:
                logger.warning("GPU monitor failed", extra={"detail": str(e)})
            await asyncio.sleep(self.monitor_interval)

    async def update_gpu_stats(self):
        async with self.lock:
            if PYNVML_AVAILABLE and not self.cpu_fallback:
                try:
                    for gid, g in self.gpus.items():
                        handle = pynvml.nvmlDeviceGetHandleByIndex(gid)
                        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        g.last_free_mb = int(mem.free / 1024 / 1024)
                        g.used_mb = int(mem.used / 1024 / 1024)
                except Exception as e:
                    logger.warning("pynvml query failed", extra={"detail": str(e)})

    async def find_suitable_gpu(self, required_mb: int, model_id: str) -> Optional[int]:
        if self.cpu_fallback or not self.gpus:
            return None
        
        await self.update_gpu_stats()
        candidates = []
        
        for gid, g in self.gpus.items():
            if g.allow_models and model_id not in g.allow_models:
                continue
            
            usable_mb = int(g.max_memory_mb * (g.max_utilization / 100.0))
            free_mb = min(g.last_free_mb, usable_mb - g.used_mb)
            
            if free_mb >= required_mb:
                candidates.append((free_mb, g))
        
        if not candidates:
            return None
        
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1].id

    async def get_metrics(self):
        if not self.gpus:
            return {}
        
        await self.update_gpu_stats()
        return {
            gid: {
                "used_mb": g.used_mb,
                "free_mb": g.last_free_mb,
                "max_mb": g.max_memory_mb
            }
            for gid, g in self.gpus.items()
        }
class RequestQueue:
    def __init__(self, db_path: str, config: Dict[str, Any]):
        self.db_path = db_path
        self.config = config
        self.pq: list = []
        self.entry_finder: Dict[str, PrioritizedItem] = {}
        self.counter = 0
        self.lock = None
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.db_lock = None

    async def initialize(self):
        if self.lock is None:
            self.lock = asyncio.Lock()
        if self.db_lock is None:
            self.db_lock = asyncio.Lock()
        
        await init_db(self.db_path)
        await self._restore_from_db()
        asyncio.create_task(self._cleanup_loop())

    async def _restore_from_db(self):
        logger.info("Restoring tasks from DB")
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT task_id, status, priority, model_id, model_params_json, "
                "input_data_json, params_json, result_json, error_text, "
                "created_at, updated_at FROM tasks"
            )
            rows = await cur.fetchall()
            
            for row in rows:
                (task_id, status, priority, model_id, model_params_json,
                 input_data_json, params_json, result_json, error_text,
                 created_at, updated_at) = row
                
                model_params = json.loads(model_params_json) if model_params_json else {}
                input_data = json.loads(input_data_json) if input_data_json else {}
                params = json.loads(params_json) if params_json else {}
                result = json.loads(result_json) if result_json else None
                
                self.tasks[task_id] = {
                    "task_id": task_id,
                    "status": status,
                    "priority": priority,
                    "model_id": model_id,
                    "model_params": model_params,
                    "input_data": input_data,
                    "params": params,
                    "result": result,
                    "error": error_text,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "stream_queue": asyncio.Queue() if params.get("stream") else None,
                }
                
                if status in ["queued", "loading_model"]:
                    await self._enqueue_in_memory(task_id, priority)
                elif status == "processing":
                    await self.set_error(task_id, "Service restarted during processing")
        
        logger.info("DB restore complete")

    async def _enqueue_in_memory(self, task_id: str, priority: int):
        self.counter += 1
        item = PrioritizedItem(priority=-priority, seq=self.counter, task_id=task_id)
        heapq.heappush(self.pq, item)
        self.entry_finder[task_id] = item

    async def add_task(self, model_id: str, priority: int, model_params: Dict[str, Any],
                      input_data: Dict[str, Any], params: Dict[str, Any]) -> str:
        if self.lock is None:
            raise RuntimeError("RequestQueue not initialized")
        
        async with self.lock:
            task_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            stream_queue = asyncio.Queue() if params.get("stream") else None
            
            self.tasks[task_id] = {
                "task_id": task_id,
                "status": "queued",
                "priority": priority,
                "model_id": model_id,
                "model_params": model_params,
                "input_data": input_data,
                "params": params,
                "result": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
                "stream_queue": stream_queue,
            }
            
            async with self.db_lock:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "INSERT INTO tasks(task_id, status, priority, model_id, "
                        "model_params_json, input_data_json, params_json, result_json, "
                        "error_text, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (task_id, "queued", priority, model_id,
                         json.dumps(model_params, ensure_ascii=False),
                         json.dumps(input_data, ensure_ascii=False),
                         json.dumps(params, ensure_ascii=False),
                         None, None, now, now)
                    )
                    await db.commit()
            
            await self._enqueue_in_memory(task_id, priority)
            logger.info("Task enqueued", extra={"detail": {
                "task_id": task_id,
                "model_id": model_id,
                "priority": priority
            }})
            return task_id

    async def pop_task(self) -> Optional[Dict[str, Any]]:
        if self.lock is None:
            return None
        
        async with self.lock:
            while self.pq:
                item = heapq.heappop(self.pq)
                task_id = item.task_id
                if task_id in self.entry_finder:
                    del self.entry_finder[task_id]
                t = self.tasks.get(task_id)
                if t:
                    return t
            return None

    async def set_status(self, task_id: str, status: str):
        t = self.tasks.get(task_id)
        if not t or self.db_lock is None:
            return
        
        t["status"] = status
        t["updated_at"] = datetime.utcnow().isoformat()
        
        async with self.db_lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
                    (status, t["updated_at"], task_id)
                )
                await db.commit()

    async def set_result(self, task_id: str, result: Any):
        t = self.tasks.get(task_id)
        if not t or self.db_lock is None:
            return
        
        t["result"] = result
        t["status"] = "completed"
        t["updated_at"] = datetime.utcnow().isoformat()
        
        async with self.db_lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE tasks SET result_json = ?, status = ?, updated_at = ? "
                    "WHERE task_id = ?",
                    (json.dumps(result, ensure_ascii=False), "completed",
                     t["updated_at"], task_id)
                )
                await db.commit()

    async def set_error(self, task_id: str, error: str):
        t = self.tasks.get(task_id)
        if not t or self.db_lock is None:
            return
        
        t["error"] = error
        t["status"] = "failed"
        t["updated_at"] = datetime.utcnow().isoformat()
        
        async with self.db_lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE tasks SET error_text = ?, status = ?, updated_at = ? "
                    "WHERE task_id = ?",
                    (error, "failed", t["updated_at"], task_id)
                )
                await db.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    async def _cleanup_loop(self):
        if self.db_lock is None:
            return
        
        ttl_days = int(self.config.get("queue", {}).get("cleanup_ttl_days", 7))
        max_history = int(self.config.get("queue", {}).get("max_history_size", 10000))
        
        while True:
            try:
                cutoff = datetime.utcnow() - timedelta(days=ttl_days)
                cutoff_iso = cutoff.isoformat()
                
                async with self.db_lock:
                    async with aiosqlite.connect(self.db_path) as db:
                        await db.execute(
                            "DELETE FROM tasks WHERE status IN ('completed', 'failed') "
                            "AND updated_at < ?",
                            (cutoff_iso,)
                        )
                        await db.commit()
                        
                        cur = await db.execute(
                            "SELECT COUNT(*) FROM tasks "
                            "WHERE status IN ('completed', 'failed')"
                        )
                        row = await cur.fetchone()
                        total = row[0] if row else 0
                        
                        if total > max_history:
                            to_remove = total - max_history
                            await db.execute(
                                "DELETE FROM tasks WHERE task_id IN "
                                "(SELECT task_id FROM tasks "
                                "WHERE status IN ('completed', 'failed') "
                                "ORDER BY updated_at ASC LIMIT ?)",
                                (to_remove,)
                            )
                            await db.commit()
                
                logger.info("Cleanup complete", extra={"detail": {
                    "ttl_days": ttl_days,
                    "max_history": max_history
                }})
            except Exception as e:
                logger.warning("Cleanup failed", extra={"detail": str(e)})
            
            await asyncio.sleep(3600)


class InferenceService:
    _instance: Optional["InferenceService"] = None

    def __init__(self, config: Dict[str, Any], request_queue: RequestQueue,
                 gpu_manager: GPUManager):
        self.config = config
        self.request_queue = request_queue
        self.gpu_manager = gpu_manager
        self.active_models: Dict[str, ModelInstance] = {}
        self.total_vram_used_mb = 0
        self.models_lock = asyncio.Lock()
        self.workers: list = []
        self.shutdown_event = asyncio.Event()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_cancel_events: Dict[str, asyncio.Event] = {}

    @classmethod
    def get_instance(cls, config: Dict[str, Any] = None,
                    request_queue: RequestQueue = None,
                    gpu_manager: GPUManager = None) -> "InferenceService":
        if cls._instance is None:
            if config is None or request_queue is None or gpu_manager is None:
                raise RuntimeError("InferenceService not initialized")
            cls._instance = cls(config, request_queue, gpu_manager)
        return cls._instance

    async def start_workers(self):
        worker_count = max(1, int(self.config.get("worker_count", 1)))
        logger.info(f"Starting {worker_count} workers")
        await self.gpu_manager.start_monitor()
        
        for i in range(worker_count):
            t = asyncio.create_task(self._worker_loop(i))
            self.workers.append(t)

    async def _worker_loop(self, worker_id: int):
        logger.info(f"Worker {worker_id} started")
        
        while not self.shutdown_event.is_set():
            task = await self.request_queue.pop_task()
            if task is None:
                await asyncio.sleep(0.1)
                continue
            
            task_id = task["task_id"]
            model_id = task["model_id"]
            model_params = task.get("model_params", {})
            input_data = task["input_data"]
            params = task["params"]
            stream_queue = task.get("stream_queue")
            
            try:
                await self.request_queue.set_status(task_id, "loading_model")
                model_instance = await self.load_model_if_needed(model_id, model_params)
                
                await self.request_queue.set_status(task_id, "processing")
                cancel_event = asyncio.Event()
                self.task_cancel_events[task_id] = cancel_event
                
                start = time.time()
                
                if stream_queue is not None:
                    result = await model_instance.infer(
                        input_data, params,
                        stream_queue=stream_queue,
                        cancel_event=cancel_event
                    )
                else:
                    result = await model_instance.infer(
                        input_data, params,
                        stream_queue=None,
                        cancel_event=cancel_event
                    )
                    await self.request_queue.set_result(task_id, result)
                
                elapsed = time.time() - start
                logger.info("Task finished", extra={"detail": {
                    "task_id": task_id,
                    "elapsed": elapsed
                }})
                
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} cancelled")
            except ModelLoadError as e:
                await self.request_queue.set_error(task_id, f"Model load failed: {e}")
            except Exception as e:
                logger.exception("Worker failed processing task")
                await self.request_queue.set_error(task_id, str(e))
            finally:
                self.running_tasks.pop(task_id, None)
                self.task_cancel_events.pop(task_id, None)
        
        logger.info(f"Worker {worker_id} stopped")

    async def load_model_if_needed(self, model_id: str,
                                   model_params: Dict[str, Any]) -> ModelInstance:
        async with self.models_lock:
            if model_id in self.active_models:
                mi = self.active_models[model_id]
                if mi.status == "ready":
                    mi.touch()
                    return mi
            
            model_path = model_params.get("model_path", model_id)
            n_gpu_layers = model_params.get("n_gpu_layers", -1)
            n_ctx = model_params.get("n_ctx", 2048)
            
            estimated_mb = int(
                self.config.get("model_vram_estimates", {}).get(
                    model_id,
                    model_params.get("estimated_vram_mb", 4096)
                )
            )
            
            mi = ModelInstance(
                model_id=model_id,
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                estimated_vram_mb=estimated_mb
            )
            
            assign_gpu = await self.gpu_manager.find_suitable_gpu(estimated_mb, model_id)
            if assign_gpu is not None:
                logger.info(f"Assigning model {model_id} to GPU {assign_gpu}")
            
            await mi.load(assign_gpu)
            
            if mi.assigned_gpu is not None:
                g = self.gpu_manager.gpus.get(mi.assigned_gpu)
                if g:
                    g.used_mb += mi.actual_vram_mb
            
            self.total_vram_used_mb += mi.estimated_vram_mb
            self.active_models[model_id] = mi
            
            logger.info(f"Model {model_id} loaded", extra={"detail": {
                "vram_mb": mi.actual_vram_mb
            }})
            return mi

    async def unload_all(self):
        logger.info("Unloading all models")
        async with self.models_lock:
            for mid in list(self.active_models.keys()):
                try:
                    await self.active_models[mid].unload()
                    if self.active_models[mid].assigned_gpu is not None:
                        g = self.gpu_manager.gpus.get(
                            self.active_models[mid].assigned_gpu
                        )
                        if g:
                            g.used_mb = max(0, g.used_mb - self.active_models[mid].actual_vram_mb)
                    
                    self.total_vram_used_mb -= self.active_models[mid].estimated_vram_mb
                    del self.active_models[mid]
                except Exception as e:
                    logger.warning(f"Error unloading {mid}", extra={"detail": str(e)})

    async def graceful_shutdown(self):
        logger.info("Graceful shutdown initiated")
        self.shutdown_event.set()
        
        for w in self.workers:
            w.cancel()
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        await self.unload_all()
        await self.gpu_manager.stop_monitor()
        
        logger.info("Shutdown complete")

    async def get_metrics(self):
        active_tasks = sum(
            1 for t in self.request_queue.tasks.values()
            if t["status"] in ["queued", "loading_model", "processing"]
        )
        
        gpu_metrics = await self.gpu_manager.get_metrics()
        loaded_models = list(self.active_models.keys())
        
        return {
            "active_tasks": active_tasks,
            "gpu_metrics": gpu_metrics,
            "loaded_models": loaded_models
        }


class ModelParams(BaseModel):
    n_gpu_layers: int = -1
    n_ctx: int = 4096
    model_path: Optional[str] = None
    estimated_vram_mb: Optional[int] = None

class InputData(BaseModel):
    type: str
    content: Any
    prompt: Optional[str] = None
    mime: Optional[str] = None

class ScheduleRequest(BaseModel):
    model_id: str
    priority: int = 0
    model_params: ModelParams = ModelParams()
    input_data: InputData
    params: Dict[str, Any] = {}

request_queue = RequestQueue(db_path=CONFIG.get("db_path", "inference_queue.db"), config=CONFIG)
gpu_manager = GPUManager(CONFIG)
gpu_manager.init_gpus()
service = InferenceService.get_instance(config=CONFIG, request_queue=request_queue, gpu_manager=gpu_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await request_queue.initialize()
    await service.start_workers()
    logger.info("Service startup complete")
    
    yield
    
    # Shutdown
    await service.graceful_shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/schedule_task")
async def schedule_task(req: ScheduleRequest, request: Request):
    known_models = CONFIG.get("model_vram_estimates", {}).keys()
    if req.model_id not in known_models and req.model_params.model_path is None:
        return JSONResponse(status_code=404, content={"detail": "Model not found"})
    
    if req.input_data.type not in ["text", "image"]:
        return JSONResponse(status_code=400, content={"detail": "Unsupported input type"})
    
    try:
        task_id = await request_queue.add_task(
            model_id=req.model_id,
            priority=req.priority,
            model_params=req.model_params.dict(),
            input_data=req.input_data.dict(),
            params=req.params
        )
        return {"task_id": task_id}
    except Exception as e:
        logger.exception("Failed to schedule task")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/task_result/{task_id}")
async def task_result(task_id: str, request: Request):
    t = request_queue.get_task(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if t.get("params", {}).get("stream"):
        if EventSourceResponse is None:
            raise HTTPException(status_code=500, detail="SSE not available")
        
        stream_q = t.get("stream_queue")
        if stream_q is None:
            raise HTTPException(status_code=500, detail="Stream queue not found")
        
        async def event_generator():
            last_heartbeat = time.time()
            heartbeat_interval = 10
            
            try:
                while True:
                    if await request.is_disconnected():
                        logger.info(f"Client disconnected for task {task_id}")
                        cancel_event = service.task_cancel_events.get(task_id)
                        if cancel_event:
                            cancel_event.set()
                        break
                    
                    if time.time() - last_heartbeat > heartbeat_interval:
                        yield ": heartbeat\n\n"
                        last_heartbeat = time.time()
                    
                    try:
                        item = await asyncio.wait_for(stream_q.get(), timeout=0.1)
                        if "event" in item and item["event"] == "done":
                            yield f"data: {json.dumps(item)}\n\n"
                            break
                        elif "event" in item and item["event"] == "error":
                            yield f"data: {json.dumps(item)}\n\n"
                            break
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.TimeoutError:
                        continue
            except Exception as e:
                logger.exception("SSE generator failed")
        
        return EventSourceResponse(event_generator())
    
    if t["status"] == "completed":
        return {"task_id": task_id, "status": t["status"], "result": t.get("result")}
    elif t["status"] == "failed":
        return {"task_id": task_id, "status": t["status"], "error": t.get("error")}
    else:
        return {"task_id": task_id, "status": t["status"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    return await service.get_metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
