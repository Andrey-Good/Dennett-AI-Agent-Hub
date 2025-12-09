import asyncio
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from agent_executor import DBInterface, NodeEvent, ExecutionRecord
import json

Base = declarative_base()

class ExecutionModel(Base):
    __tablename__ = "executions"
    execution_id = Column(String(255), primary_key=True)
    agent_id = Column(String(255))
    status = Column(String(50))
    started_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
    final_result = Column(Text, nullable=True)

class NodeEventModel(Base):
    __tablename__ = "node_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255))
    node_id = Column(String(255))
    status = Column(String(50))
    timestamp = Column(DateTime)
    intermediate_output = Column(Text, nullable=True)
    error_log = Column(Text, nullable=True)

class RealDB(DBInterface):
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def init_db(self):
        Base.metadata.create_all(self.engine)
        logger.info("Database tables initialized")
    
    async def get_node_event(self, execution_id: str, node_id: str) -> Optional[Dict]:
        session: Session = self.SessionLocal()
        try:
            event = session.query(NodeEventModel).filter(
                NodeEventModel.execution_id == execution_id,
                NodeEventModel.node_id == node_id,
                NodeEventModel.status == "COMPLETED"
            ).order_by(NodeEventModel.timestamp.desc()).first()
            
            if event:
                return {
                    "execution_id": event.execution_id,
                    "node_id": event.node_id,
                    "status": event.status,
                    "intermediate_output": event.intermediate_output,
                }
            return None
        finally:
            session.close()
    
    async def save_node_event(self, event: NodeEvent):
        session: Session = self.SessionLocal()
        try:
            db_event = NodeEventModel(
                execution_id=event.execution_id,
                node_id=event.node_id,
                status=event.status,
                timestamp=datetime.fromisoformat(event.timestamp),
                intermediate_output=event.intermediate_output,
                error_log=event.error_log,
            )
            session.add(db_event)
            session.commit()
            logger.debug(f"Saved event: {event.node_id} -> {event.status}")
        finally:
            session.close()
    
    async def get_execution_events(self, execution_id: str):
        session: Session = self.SessionLocal()
        try:
            events = session.query(NodeEventModel).filter(
                NodeEventModel.execution_id == execution_id
            ).order_by(NodeEventModel.timestamp).all()
            
            return [{
                "execution_id": e.execution_id,
                "node_id": e.node_id,
                "status": e.status,
                "timestamp": e.timestamp.isoformat(),
                "intermediate_output": e.intermediate_output,
            } for e in events]
        finally:
            session.close()
    
    async def update_execution_status(
        self,
        execution_id: str,
        status: str,
        final_result: Optional[str] = None
    ):
        session: Session = self.SessionLocal()
        try:
            exec_model = session.query(ExecutionModel).filter(
                ExecutionModel.execution_id == execution_id
            ).first()
            
            if exec_model:
                exec_model.status = status
                exec_model.final_result = final_result
                if status in ["COMPLETED", "FAILED", "CANCELLED"]:
                    exec_model.completed_at = datetime.utcnow()
                session.commit()
                logger.info(f"Updated execution {execution_id} -> {status}")
        finally:
            session.close()
    
    async def save_execution_record(self, record: ExecutionRecord):
        session: Session = self.SessionLocal()
        try:
            exec_model = ExecutionModel(
                execution_id=record.execution_id,
                agent_id=record.agent_id,
                status=record.status,
                started_at=datetime.fromisoformat(record.started_at),
            )
            session.add(exec_model)
            session.commit()
            logger.info(f"Created execution {record.execution_id}")
        finally:
            session.close()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketEmitter:
    def __init__(self):
        self.active_connections: Dict[str, list] = {}
    
    def add_connection(self, execution_id: str, websocket):
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = []
        self.active_connections[execution_id].append(websocket)
        logger.debug(f"WebSocket connected for {execution_id}")
    
    def remove_connection(self, execution_id: str, websocket):
        if execution_id in self.active_connections:
            self.active_connections[execution_id].remove(websocket)
    
    async def emit(self, execution_id: str, event_type: str, data: Any = None):
        if execution_id not in self.active_connections:
            return
        
        message = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        for ws in self.active_connections[execution_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send event: {e}")

from agent_executor import NodeRegistry, NodeResult

registry = NodeRegistry()

def input_node(context):
    return NodeResult(
        status="success",
        output={"user_input": context.get("user_input", "")}
    ).dict()

registry.register("input_start", input_node)

async def fetch_user_data(context):
    user_id = context.get("user_id")
    
    try:
        await asyncio.sleep(1)
        
        user_data = {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }
        
        return NodeResult(
            status="success",
            output={"user_data": user_data}
        ).dict()
    
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return NodeResult(
            status="error",
            output={"error": str(e)}
        ).dict()

registry.register("fetch_user", fetch_user_data)

async def process_user(context):
    user_data = context.get("user_data", {})
    
    if not user_data:
        return NodeResult(
            status="error",
            output={"error": "No user data"}
        ).dict()
    
    processed = {
        **user_data,
        "processed_at": datetime.utcnow().isoformat(),
        "status": "processed",
        "tags": ["important", "vip"] if user_data.get("id", 0) > 100 else ["normal"]
    }
    
    return NodeResult(
        status="success",
        output={"processed_user": processed}
    ).dict()

registry.register("process_user", process_user)

async def save_user(context):
    processed_user = context.get("processed_user", {})
    await asyncio.sleep(0.5)
    return NodeResult(
        status="success",
        output={
            "saved": True,
            "user_id": processed_user.get("id"),
            "message": f"User {processed_user.get('name')} saved"
        }
    ).dict()

registry.register("save_user", save_user)

AGENT_CONFIG = {
    "graph": {
        "nodes": [
            {
                "id": "start",
                "type": "input_start",
                "config": {},
                "input_map": {}
            },
            {
                "id": "fetch",
                "type": "fetch_user",
                "config": {"timeout": 30},
                "input_map": {"user_id": "user_id"}
            },
            {
                "id": "process",
                "type": "process_user",
                "config": {},
                "input_map": {"user_data": "user_data"}
            },
            {
                "id": "save",
                "type": "save_user",
                "config": {},
                "input_map": {"processed_user": "processed_user"}
            }
        ],
        "edges": [
            {"source": "start", "target": "fetch", "type": "default"},
            {"source": "fetch", "target": "process", "type": "default"},
            {"source": "process", "target": "save", "type": "default"}
        ]
    }
}

from agent_executor import AgentExecutor, ArtifactManager
import uuid

async def run_agent_production(user_id: int, emitter=None):
    execution_id = f"exec_{user_id}_{uuid.uuid4().hex[:8]}"
    logger.info(f"Starting execution {execution_id}")
    
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/agent_db")
        db = RealDB(db_url)
        artifact_manager = ArtifactManager(base_dir="./artifacts")
        
        executor = AgentExecutor(
            agent_config=AGENT_CONFIG,
            execution_id=execution_id,
            db_session=db,
            event_emitter=emitter or (lambda e, d: None),
            artifact_manager=artifact_manager,
            registry=registry,
        )
        
        from agent_executor import ExecutionRecord
        record = ExecutionRecord(
            execution_id=execution_id,
            agent_id="production_agent_v1",
            status="RUNNING",
            started_at=datetime.utcnow().isoformat()
        )
        await db.save_execution_record(record)
        
        result = await executor.run({"user_id": user_id})
        logger.info(f"✅ Execution {execution_id} completed")
        return result
    
    except asyncio.CancelledError:
        logger.warning(f"❌ Execution {execution_id} cancelled")
        raise
    
    except Exception as e:
        logger.error(f"❌ Execution {execution_id} failed: {e}")
        raise

class GracefulShutdown:
    def __init__(self):
        self.tasks = []
    
    def add_task(self, task):
        self.tasks.append(task)
    
    async def shutdown(self):
        logger.info("Graceful shutdown initiated...")
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("All tasks cancelled")

async def test_production_setup():
    logger.info("Testing production setup...")
    from agent_executor_guide import RealDB as SimpleDB
    
    class TestDB(SimpleDB):
        pass
    
    db = TestDB()
    
    def mock_emitter(event_type, data):
        logger.info(f"📡 {event_type}: {data}")
    
    try:
        result = await run_agent_production(
            user_id=123,
            emitter=mock_emitter
        )
        logger.info(f"Test passed! Result: {result}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    print("Production integration example configured.")
    print("\nTo use in real project:")
    print("1. Set DATABASE_URL env var")
    print("2. Create PostgreSQL database")
    print("3. Import and use run_agent_production()")
    print("4. Integrate with FastAPI/Flask for HTTP API")
