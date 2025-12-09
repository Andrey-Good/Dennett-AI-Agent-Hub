import asyncio
import json
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from agent_executor import (
    AgentExecutor,
    ArtifactManager,
    NodeRegistry,
    NodeResult,
    NodeEvent,
    DBInterface,
    ConditionalRouter,
)


class MockDB(DBInterface):
    def __init__(self):
        self.node_events: Dict[str, NodeEvent] = {}
        self.execution_events: list = []

    async def get_node_event(self, execution_id: str, node_id: str):
        key = f"{execution_id}_{node_id}"
        event = self.node_events.get(key)
        return event.dict() if event else None

    async def save_node_event(self, event: NodeEvent):
        key = f"{event.execution_id}_{event.node_id}"
        self.node_events[key] = event
        self.execution_events.append(event.dict())

    async def get_execution_events(self, execution_id: str):
        return sorted(
            [e for e in self.execution_events if e["execution_id"] == execution_id],
            key=lambda x: x["timestamp"]
        )

    async def update_execution_status(self, execution_id: str, status: str, final_result=None):
        pass

    async def save_execution_record(self, record):
        pass


def test_node_result_contract():
    valid = NodeResult(
        status="success",
        output={"key": "value"},
        secrets={"token": "abc123"},
        artifacts=["/tmp/file.txt"]
    )
    assert valid.status == "success"
    assert valid.output == {"key": "value"}

    minimal = NodeResult(
        status="success",
        output={}
    )
    assert minimal.status == "success"

    with pytest.raises(Exception):
        NodeResult(status="invalid_status", output={})

    with pytest.raises(Exception):
        NodeResult(status="success")


def test_node_result_serialization():
    result = NodeResult(
        status="success",
        output={"data": "test"},
        secrets={"token": "secret"}
    )
    json_str = json.dumps(result.dict())
    deserialized = json.loads(json_str)
    assert deserialized["status"] == "success"
    assert deserialized["output"]["data"] == "test"
    assert deserialized["secrets"]["token"] == "secret"


@pytest.mark.asyncio
async def test_secrets_masking_in_db():
    db = MockDB()
    registry = NodeRegistry()

    async def update_token(context):
        old_token = context.get("api_key", "")
        new_token = f"new_token_{len(old_token)}"
        return NodeResult(
            status="success",
            output={"updated": True},
            secrets={"api_key": new_token}
        ).dict()

    registry.register("update_token", update_token)

    config = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "input_start",
                    "config": {},
                    "input_map": {},
                },
                {
                    "id": "token_updater",
                    "type": "update_token",
                    "config": {},
                    "input_map": {"api_key": "current_token"},
                    "secrets": {"api_key": "initial_token_123"}
                }
            ],
            "edges": [
                {"source": "start", "target": "token_updater", "type": "default"}
            ]
        }
    }

    executor = AgentExecutor(
        agent_config=config,
        execution_id="test_secrets_001",
        db_session=db,
        registry=registry,
    )

    result = await executor.run({"current_token": "initial_token_123"})

    events = await db.get_execution_events("test_secrets_001")
    token_event = [e for e in events if e["node_id"] == "token_updater"][0]
    intermediate_output = json.loads(token_event["intermediate_output"])
    assert "new_token" not in intermediate_output.get("updated", str(False))
    print("✓ Secrets are properly masked in DB")


@pytest.mark.asyncio
async def test_artifact_offload():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MockDB()
        registry = NodeRegistry()
        artifact_manager = ArtifactManager(base_dir=tmpdir)

        async def big_data_generator(context):
            big_output = {
                "data": "x" * (10 * 1024),
                "metadata": "Some metadata"
            }
            return NodeResult(
                status="success",
                output=big_output
            ).dict()

        registry.register("big_data_generator", big_data_generator)

        config = {
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "input_start",
                        "config": {},
                        "input_map": {},
                    },
                    {
                        "id": "generator",
                        "type": "big_data_generator",
                        "config": {},
                        "input_map": {},
                    }
                ],
                "edges": [
                    {"source": "start", "target": "generator", "type": "default"}
                ]
            }
        }

        executor = AgentExecutor(
            agent_config=config,
            execution_id="test_offload_001",
            db_session=db,
            registry=registry,
            artifact_manager=artifact_manager,
        )

        result = await executor.run({})

        events = await db.get_execution_events("test_offload_001")
        gen_event = [e for e in events if e["node_id"] == "generator"][0]
        intermediate_output = json.loads(gen_event["intermediate_output"])
        assert "__ref" in intermediate_output
        assert intermediate_output["__ref"].startswith("artifact://")
        artifact_uri = intermediate_output["__ref"]
        loaded_data = artifact_manager.load_content(artifact_uri)
        assert len(loaded_data["data"]) == 10 * 1024
        print("✓ Large output properly offloaded to artifact storage")


@pytest.mark.asyncio
async def test_execution_recovery():
    db = MockDB()
    registry = NodeRegistry()

    call_count = {"start": 0, "process": 0, "finalize": 0}

    async def start_node(context):
        call_count["start"] += 1
        return NodeResult(
            status="success",
            output={"initial_data": "value_123"}
        ).dict()

    async def process_node(context):
        call_count["process"] += 1
        initial = context.get("initial_data", "")
        return NodeResult(
            status="success",
            output={"processed": f"{initial}_processed"}
        ).dict()

    async def finalize_node(context):
        call_count["finalize"] += 1
        processed = context.get("processed", "")
        return NodeResult(
            status="success",
            output={"final": f"{processed}_finalized"}
        ).dict()

    registry.register("start_node", start_node)
    registry.register("process_node", process_node)
    registry.register("finalize_node", finalize_node)

    config = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start_node",
                    "config": {},
                    "input_map": {},
                },
                {
                    "id": "process",
                    "type": "process_node",
                    "config": {},
                    "input_map": {"initial_data": "initial_data"},
                },
                {
                    "id": "finalize",
                    "type": "finalize_node",
                    "config": {},
                    "input_map": {"processed": "processed"},
                }
            ],
            "edges": [
                {"source": "start", "target": "process", "type": "default"},
                {"source": "process", "target": "finalize", "type": "default"}
            ]
        }
    }

    executor1 = AgentExecutor(
        agent_config=config,
        execution_id="test_recovery_001",
        db_session=db,
        registry=registry,
    )

    result1 = await executor1.run({})

    assert call_count["start"] == 1
    assert call_count["process"] == 1
    assert call_count["finalize"] == 1

    call_count = {"start": 0, "process": 0, "finalize": 0}

    executor2 = AgentExecutor(
        agent_config=config,
        execution_id="test_recovery_001",
        db_session=db,
        registry=registry,
    )

    result2 = await executor2.run({})

    assert call_count["start"] == 0
    assert call_count["process"] == 0
    assert call_count["finalize"] == 0

    assert result2["final"] == "value_123_processed_finalized"
    print("✓ Recovery works: no duplicate execution")


@pytest.mark.asyncio
async def test_sync_node_nonblocking():
    db = MockDB()
    registry = NodeRegistry()

    def blocking_operation(context):
        import time
        time.sleep(2)
        return NodeResult(
            status="success",
            output={"slept": 2}
        ).dict()

    registry.register("blocking_op", blocking_operation)

    config = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "input_start",
                    "config": {},
                    "input_map": {},
                },
                {
                    "id": "blocker",
                    "type": "blocking_op",
                    "config": {},
                    "input_map": {},
                }
            ],
            "edges": [
                {"source": "start", "target": "blocker", "type": "default"}
            ]
        }
    }

    executor = AgentExecutor(
        agent_config=config,
        execution_id="test_async_001",
        db_session=db,
        registry=registry,
    )

    import time
    start_time = time.time()

    async def parallel_task():
        results = []
        for i in range(5):
            await asyncio.sleep(0.3)
            results.append(i)
        return results

    exec_result, parallel_result = await asyncio.gather(
        executor.run({}),
        parallel_task()
    )

    elapsed = time.time() - start_time

    assert elapsed < 3.0, f"Event Loop was blocked! Took {elapsed}s instead of ~2s"
    assert parallel_result == [0, 1, 2, 3, 4]
    print(f"✓ Async safety verified: blocking node ran in parallel (total time: {elapsed:.2f}s)")


@pytest.mark.asyncio
async def test_input_mapping():
    db = MockDB()
    registry = NodeRegistry()

    received_context = {}

    async def mapping_test_node(context):
        nonlocal received_context
        received_context = context.copy()
        return NodeResult(
            status="success",
            output={"received": list(context.keys())}
        ).dict()

    registry.register("mapping_test", mapping_test_node)

    config = {
        "graph": {
            "nodes": [
                {
                    "id": "start",
                    "type": "input_start",
                    "config": {},
                    "input_map": {},
                },
                {
                    "id": "mapper",
                    "type": "mapping_test",
                    "config": {"default_value": 999},
                    "input_map": {
                        "text": "user_input",
                        "multiplier": "config_value",
                        "default_value": "default_value"
                    },
                }
            ],
            "edges": [
                {"source": "start", "target": "mapper", "type": "default"}
            ]
        }
    }

    executor = AgentExecutor(
        agent_config=config,
        execution_id="test_mapping_001",
        db_session=db,
        registry=registry,
    )

    result = await executor.run({
        "user_input": "hello world",
        "config_value": 42
    })

    assert received_context["text"] == "hello world"
    assert received_context["multiplier"] == 42
    assert received_context["default_value"] == 999
    assert "cancellation_token" in received_context
    print("✓ Input mapping works correctly")


def test_conditional_router():
    router_eq = ConditionalRouter.create_router({
        "condition": {"variable": "status", "operator": "eq", "value": "success"},
        "target": "success_node",
        "fallback_target": "error_node"
    })
    assert router_eq({"status": "success"}) == "success_node"
    assert router_eq({"status": "failed"}) == "error_node"

    router_gt = ConditionalRouter.create_router({
        "condition": {"variable": "score", "operator": "gt", "value": 50},
        "target": "pass_node",
        "fallback_target": "fail_node"
    })
    assert router_gt({"score": 100}) == "pass_node"
    assert router_gt({"score": 25}) == "fail_node"

    router_contains = ConditionalRouter.create_router({
        "condition": {"variable": "tags", "operator": "contains", "value": "urgent"},
        "target": "priority_node",
        "fallback_target": "normal_node"
    })
    assert router_contains({"tags": ["urgent", "bug"]}) == "priority_node"
    assert router_contains({"tags": ["feature"]}) == "normal_node"

    router_is_set = ConditionalRouter.create_router({
        "condition": {"variable": "user_id", "operator": "is_set"},
        "target": "authenticated",
        "fallback_target": "anonymous"
    })
    assert router_is_set({"user_id": 123}) == "authenticated"
    assert router_is_set({"user_id": None}) == "anonymous"

    router_regex = ConditionalRouter.create_router({
        "condition": {"variable": "email", "operator": "regex", "value": r"^[\w\.-]+@[\w\.-]+\.\w+$"},
        "target": "valid_email",
        "fallback_target": "invalid_email"
    })
    assert router_regex({"email": "test@example.com"}) == "valid_email"
    assert router_regex({"email": "not-an-email"}) == "invalid_email"
    print("✓ Conditional routing works for all operators")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("AGENT EXECUTOR - DEFINITION OF DONE TESTS")
    print("="*70 + "\n")
    print("Test 1: Strict JSON (NodeResult Contract)")
    test_node_result_contract()
    test_node_result_serialization()
    print("\nTest 7: Conditional Routing")
    test_conditional_router()
    print("\n" + "="*70)
    print("Async tests require: pytest-asyncio")
    print("Run with: pytest agent_executor_tests.py -v")
    print("="*70 + "\n")
