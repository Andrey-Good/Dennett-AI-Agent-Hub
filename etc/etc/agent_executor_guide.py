from agent_executor import NodeRegistry, NodeResult
import asyncio
from typing import Dict, Any

registry = NodeRegistry()

def sync_calculator(context: Dict[str, Any]) -> Dict[str, Any]:
    number = context.get("input_number", 0)
    multiplier = context.get("multiplier", 1)
    result = number * multiplier
    return NodeResult(
        status="success",
        output={"calculation_result": result}
    ).dict()

registry.register("sync_calculator", sync_calculator)

async def async_api_call(context: Dict[str, Any]) -> Dict[str, Any]:
    api_endpoint = context.get("endpoint", "")
    session_token = context.get("session_token")
    await asyncio.sleep(1)
    api_response = {"status": "ok", "data": "Some API response"}
    return NodeResult(
        status="success",
        output={"api_data": api_response},
        secrets={"session_token": "new_token_xyz"}
    ).dict()

registry.register("async_api_call", async_api_call)

async def risky_operation(context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        value = context.get("risky_value")
        if value < 0:
            raise ValueError("Value cannot be negative")
        result = 100 / value
        return NodeResult(
            status="success",
            output={"result": result}
        ).dict()
    except ZeroDivisionError:
        return NodeResult(
            status="error",
            output={"error_message": "Division by zero"}
        ).dict()
    except Exception as e:
        raise

registry.register("risky_operation", risky_operation)

async def long_running_task(context: Dict[str, Any]) -> Dict[str, Any]:
    cancellation_token = context.get("cancellation_token")
    for step in range(100):
        if cancellation_token and cancellation_token.is_set():
            raise asyncio.CancelledError("Task cancelled by user")
        await asyncio.sleep(0.1)
        print(f"Step {step}/100 complete")
    return NodeResult(
        status="success",
        output={"completed_steps": 100}
    ).dict()

registry.register("long_running_task", long_running_task)

async def generate_report(context: Dict[str, Any]) -> Dict[str, Any]:
    report_data = {
        "title": "Quarterly Report",
        "sections": [f"Section {i}" for i in range(1000)],
        "size_mb": 5.2
    }
    return NodeResult(
        status="success",
        output={"report": report_data},
        artifacts=["/tmp/report_2024_q4.pdf"]
    ).dict()

registry.register("generate_report", generate_report)

EXAMPLE_AGENT_CONFIG = {
    "graph": {
        "nodes": [
            {"id": "start", "type": "input_start", "config": {}, "input_map": {}},
            {
                "id": "calculator",
                "type": "sync_calculator",
                "config": {"multiplier": 2},
                "input_map": {"input_number": "user_number", "multiplier": "custom_multiplier"},
                "secrets": {}
            },
            {
                "id": "api_call",
                "type": "async_api_call",
                "config": {"endpoint": "https://api.example.com/data"},
                "input_map": {"endpoint": "api_endpoint", "session_token": "session_token"},
                "secrets": {"session_token": "initial_token_123"}
            },
            {
                "id": "process",
                "type": "risky_operation",
                "config": {},
                "input_map": {"risky_value": "api_data"}
            },
            {"id": "long_task", "type": "long_running_task", "config": {}, "input_map": {}},
            {"id": "report", "type": "generate_report", "config": {}, "input_map": {}}
        ],
        "edges": [
            {"source": "start", "target": "calculator", "type": "default"},
            {
                "source": "calculator",
                "type": "conditional",
                "condition": {"variable": "calculation_result", "operator": "gt", "value": 10},
                "target": "api_call",
                "fallback_target": "process"
            },
            {
                "source": "api_call",
                "type": "conditional",
                "condition": {"variable": "api_data", "operator": "regex", "value": "^success.*"},
                "target": "long_task",
                "fallback_target": "report"
            },
            {"source": "long_task", "target": "report", "type": "default"}
        ]
    }
}

import asyncio
from agent_executor import AgentExecutor, ArtifactManager, DBInterface
from agent_executor import NodeEvent, ExecutionRecord
from typing import Optional

class RealDB(DBInterface):
    def __init__(self):
        self.node_events = {}
        self.execution_events = []

    async def get_node_event(self, execution_id: str, node_id: str):
        key = f"{execution_id}_{node_id}"
        event = self.node_events.get(key)
        return event.dict() if event else None

    async def save_node_event(self, event: NodeEvent):
        key = f"{event.execution_id}_{event.node_id}"
        self.node_events[key] = event
        self.execution_events.append(event.dict())

    async def get_execution_events(self, execution_id: str):
        return [e for e in self.execution_events if e["execution_id"] == execution_id]

    async def update_execution_status(self, execution_id: str, status: str, final_result: Optional[str] = None):
        print(f"✓ Execution {execution_id} -> {status}")

    async def save_execution_record(self, record: ExecutionRecord):
        print(f"✓ Saved execution record: {record.execution_id}")

def event_emitter(event_type: str, data: Any = None):
    print(f"📡 Event [{event_type}]: {data}")

async def run_agent_example():
    db = RealDB()
    artifact_manager = ArtifactManager(base_dir="/tmp/artifacts")
    executor = AgentExecutor(
        agent_config=EXAMPLE_AGENT_CONFIG,
        execution_id="exec_demo_001",
        db_session=db,
        event_emitter=event_emitter,
        artifact_manager=artifact_manager,
        registry=registry,
    )
    input_data = {"user_number": 25, "custom_multiplier": 3, "api_endpoint": "https://api.custom.com/data"}
    try:
        result = await executor.run(input_data)
        print(f"\n✅ SUCCESS! Final result: {result}")
        return result
    except asyncio.CancelledError:
        print("❌ Execution was cancelled")
        raise
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        raise

async def recovery_example():
    print("="*60)
    print("SCENARIO: Process crashed, now recovering...")
    print("="*60)
    db = RealDB()
    await db.save_node_event(NodeEvent(
        execution_id="exec_crash_001",
        node_id="start",
        status="COMPLETED",
        timestamp="2024-01-01T10:00:00",
        intermediate_output='{"user_number": 25}'
    ))
    await db.save_node_event(NodeEvent(
        execution_id="exec_crash_001",
        node_id="calculator",
        status="COMPLETED",
        timestamp="2024-01-01T10:00:01",
        intermediate_output='{"calculation_result": 50}'
    ))
    await db.save_node_event(NodeEvent(
        execution_id="exec_crash_001",
        node_id="api_call",
        status="COMPLETED",
        timestamp="2024-01-01T10:00:02",
        intermediate_output='{"api_data": 150}'
    ))
    print("✓ Simulated previous execution history in DB")
    executor = AgentExecutor(
        agent_config=EXAMPLE_AGENT_CONFIG,
        execution_id="exec_crash_001",
        db_session=db,
        event_emitter=event_emitter,
        registry=registry,
    )
    print("✓ Recovery logic:")
    print("  1. Loaded execution history from DB")
    print("  2. Re-hydrated state")
    print("  3. Graph execution continues")

async def batch_processor(context: Dict[str, Any]) -> Dict[str, Any]:
    items = context.get("items", [])
    batch_size = context.get("batch_size", 10)
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        processed = [f"processed_{item}" for item in batch]
        results.extend(processed)
        await asyncio.sleep(0.01)
    return NodeResult(
        status="success",
        output={"processed_items": results, "total": len(results)}
    ).dict()

registry.register("batch_processor", batch_processor)

async def api_with_fallback(context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        primary_endpoint = context.get("primary_endpoint")
        data = {"source": "primary", "data": "fresh"}
    except Exception:
        data = {"source": "cache", "data": "stale"}
    return NodeResult(status="success", output={"result": data}).dict()

registry.register("api_with_fallback", api_with_fallback)

async def router_node(context: Dict[str, Any]) -> Dict[str, Any]:
    user_type = context.get("user_type", "guest")
    route = "vip_flow" if user_type == "vip" else "standard_flow"
    return NodeResult(status="success", output={"route": route, "user_type": user_type}).dict()

registry.register("router_node", router_node)

if __name__ == "__main__":
    print("AgentExecutor Usage Guide")
    print("=" * 60)
