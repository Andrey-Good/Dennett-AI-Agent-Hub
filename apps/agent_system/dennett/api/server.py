# dennett/api/server.py
"""
FastAPI server: REST API + WebSocket for Dennett Core v5.0.
"""

import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import json

# Global state
app = FastAPI(title="Dennett AI Core v5.0", version="5.0")

db = None
enqueue_service = None
event_hub = None
agent_worker = None
inference_worker = None
startup_ts = None

@app.on_event("startup")
async def startup_event():
    """Initialize core on startup."""
    global db, enqueue_service, event_hub, agent_worker, inference_worker, startup_ts
    
    startup_ts = datetime.utcnow().timestamp()
    
    from dennett.core.db import DatabaseManager
    from dennett.core.priority import PriorityPolicy
    from dennett.core.enqueue import EnqueueService
    from dennett.core.recovery import StartupRecovery
    from dennett.core.eventhub import EventHub
    
    # Initialize DB
    db = DatabaseManager()
    event_hub = EventHub()
    priority_policy = PriorityPolicy(db)
    enqueue_service = EnqueueService(db, priority_policy)
    
    # Recover from crash
    StartupRecovery.recover(db)
    
    # Start aging worker
    asyncio.create_task(priority_policy.run_aging_worker())
    
    print("✅ Dennett Core started")

# ============== REST API ==============

@app.post("/executions/run")
async def run_execution(payload: dict):
    """POST /executions/run - Start agent execution."""
    try:
        execution_id = enqueue_service.enqueue_execution(
            agent_id=payload.get("agent_id"),
            payload=payload.get("input", {}),
            source="MANUAL_RUN",
        )
        return {
            "execution_id": execution_id,
            "status": "QUEUED",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """GET /executions/{id} - Get execution status and results."""
    try:
        query = "SELECT * FROM executions WHERE execution_id = :execution_id"
        row = db.execute_query(query, {"execution_id": execution_id})
        
        if not row:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        result = dict(row)
        # Parse JSON fields
        if result.get("final_result"):
            result["final_result"] = json.loads(result["final_result"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """POST /executions/{id}/cancel - Cancel execution."""
    try:
        # Update to CANCEL_REQUESTED
        query = """
            UPDATE executions
            SET status = 'CANCEL_REQUESTED'
            WHERE execution_id = :execution_id
        """
        count = db.execute_update(query, {"execution_id": execution_id})
        
        if count == 0:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Signal cancel to worker if running
        if agent_worker and execution_id in agent_worker.running_executions:
            await agent_worker.cancel_execution(execution_id)
        
        return {"status": "cancel_requested", "execution_id": execution_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/inference/chat")
async def chat_inference(payload: dict):
    """POST /inference/chat - Start inference task."""
    try:
        task_id = enqueue_service.enqueue_inference(
            model_id=payload.get("model_id"),
            messages=payload.get("messages", []),
            parameters=payload.get("parameters", {}),
            source="CHAT",
        )
        return {
            "task_id": task_id,
            "status": "QUEUED",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/inference/{task_id}")
async def get_inference(task_id: str):
    """GET /inference/{task_id} - Get inference status."""
    try:
        query = "SELECT * FROM inference_queue WHERE task_id = :task_id"
        row = db.execute_query(query, {"task_id": task_id})
        
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        
        result = dict(row)
        # Parse JSON fields
        if result.get("result"):
            result["result"] = json.loads(result["result"])
        if result.get("prompt"):
            result["prompt"] = json.loads(result["prompt"])
        if result.get("parameters"):
            result["parameters"] = json.loads(result["parameters"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/inference/{task_id}/cancel")
async def cancel_inference(task_id: str):
    """POST /inference/{task_id}/cancel - Cancel inference."""
    try:
        query = """
            UPDATE inference_queue
            SET status = 'CANCEL_REQUESTED'
            WHERE task_id = :task_id
        """
        count = db.execute_update(query, {"task_id": task_id})
        
        if count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Signal cancel to worker if running
        if inference_worker and task_id in inference_worker.running_inference:
            await inference_worker.cancel_inference(task_id)
        
        return {"status": "cancel_requested", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/health")
async def health():
    """GET /admin/health - Health check endpoint."""
    try:
        uptime_sec = int(datetime.utcnow().timestamp() - startup_ts) if startup_ts else 0
        
        # Get SQLite version
        version_row = db.execute_query("SELECT sqlite_version() as version")
        sqlite_version = version_row["version"] if version_row else "unknown"
        
        return {
            "status": "ok",
            "sqlite_version": sqlite_version,
            "uptime_sec": uptime_sec,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }, 500

# ============== WebSocket ==============

@app.websocket("/inference/{task_id}/stream")
async def websocket_inference_stream(websocket: WebSocket, task_id: str):
    """WS /inference/{task_id}/stream - Stream inference tokens in realtime."""
    await websocket.accept()
    
    try:
        # Check task exists
        query = "SELECT status FROM inference_queue WHERE task_id = ?"
        task = db.execute_query(query, {"task_id": task_id})
        
        if not task:
            await websocket.close(code=4004, reason="Task not found")
            return
        
        print(f"🔌 WebSocket client connected for inference:{task_id[:8]}")
        
        # Subscribe to event channel
        async def on_event(event: dict):
            try:
                await websocket.send_json(event)
            except Exception as e:
                print(f"❌ WebSocket send error: {e}")
        
        event_hub.subscribe(f"inference:{task_id}", on_event)
        
        try:
            # Keep connection alive
            while True:
                # Wait for client message (keep-alive ping or close)
                try:
                    msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    # Client can send "ping" or any message to keep connection alive
                except asyncio.TimeoutError:
                    # Send ping every 30s to keep connection alive
                    try:
                        await websocket.send_json({"type": "PING"})
                    except:
                        break
        except Exception as e:
            print(f"⚠️  WebSocket error: {e}")
        
    finally:
        event_hub.unsubscribe(f"inference:{task_id}", on_event)
        print(f"🔌 WebSocket client disconnected for inference:{task_id[:8]}")
