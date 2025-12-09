import asyncio
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import re

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

logger = logging.getLogger("agent_executor")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class NodeResult(BaseModel):
    status: str = Field(..., pattern="^(success|error|interrupted)$")
    output: Dict[str, Any] = Field(default_factory=dict)
    secrets: Optional[Dict[str, str]] = Field(default=None)
    artifacts: Optional[List[str]] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True


class NodeEvent(BaseModel):
    execution_id: str
    node_id: str
    status: str
    timestamp: str
    intermediate_output: Optional[str] = None
    error_log: Optional[str] = None


class ExecutionRecord(BaseModel):
    execution_id: str
    agent_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    final_result: Optional[str] = None


class ArtifactManager:
    def __init__(self, base_dir: str = "artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ArtifactManager initialized at {self.base_dir.resolve()}")

    def _ensure_execution_dir(self, execution_id: str) -> Path:
        exec_dir = self.base_dir / execution_id
        exec_dir.mkdir(parents=True, exist_ok=True)
        return exec_dir

    def save_content(self, execution_id: str, node_id: str, data: Any) -> str:
        exec_dir = self._ensure_execution_dir(execution_id)
        timestamp = datetime.utcnow().isoformat().replace(':', '-').replace('.', '-')
        is_binary = isinstance(data, bytes)
        ext = ".bin" if is_binary else ".json"
        filename = f"{node_id}_{timestamp}{ext}"
        file_path = exec_dir / filename

        if is_binary:
            with open(file_path, 'wb') as f:
                f.write(data)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, default=str)

        uri = f"artifact://{execution_id}/{filename}"
        logger.debug(f"Saved artifact: {uri} (size: {file_path.stat().st_size} bytes)")
        return uri

    def load_content(self, uri: str) -> Any:
        if not uri.startswith("artifact://"):
            raise ValueError(f"Invalid artifact URI: {uri}")

        path_part = uri[len("artifact://"):]
        file_path = self.base_dir / path_part

        if not file_path.exists():
            raise FileNotFoundError(f"CRITICAL: Artifact lost! URI={uri}, Path={file_path.resolve()}")

        if file_path.suffix == ".json":
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(file_path, 'rb') as f:
                return f.read()

    def should_offload(self, data: Any, threshold_kb: float = 5.0) -> bool:
        if isinstance(data, bytes):
            return (len(data) / 1024) > threshold_kb
        try:
            size_bytes = len(json.dumps(data, default=str).encode('utf-8'))
            return (size_bytes / 1024) > threshold_kb
        except TypeError:
            return True


class NodeRegistry:
    def __init__(self):
        self._implementations: Dict[str, Callable] = {}
        logger.info("NodeRegistry initialized")

    def register(self, node_type: str, func: Callable) -> None:
        self._implementations[node_type] = func
        logger.debug(f"Registered node type: {node_type}")

    def get_implementation(self, node_type: str) -> Callable:
        if node_type not in self._implementations:
            raise ValueError(f"Unknown node type: {node_type}")
        return self._implementations[node_type]

    def validate_node_types(self, node_types: List[str]) -> List[str]:
        return [nt for nt in set(node_types) if nt not in self._implementations]


class DBInterface(ABC):
    @abstractmethod
    async def get_node_event(self, execution_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save_node_event(self, event: NodeEvent) -> None:
        pass

    @abstractmethod
    async def get_execution_events(self, execution_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_execution_status(self, execution_id: str, status: str, final_result: Optional[str] = None) -> None:
        pass


class ConditionalRouter:
    OPERATORS = {
        "eq": lambda a, b: a == b,
        "neq": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "lt": lambda a, b: a < b,
        "gte": lambda a, b: a >= b,
        "lte": lambda a, b: a <= b,
        "contains": lambda a, b: b in a if a is not None else False,
        "is_set": lambda a, _: a is not None,
    }

    @staticmethod
    def create_router(edge_config: Dict[str, Any]) -> Callable:
        condition = edge_config.get("condition", {})
        variable = condition.get("variable")
        operator = condition.get("operator", "eq")
        expected_value = condition.get("value")
        target = edge_config.get("target")
        fallback = edge_config.get("fallback_target")

        if not all([variable, operator, target, fallback]):
            raise ValueError(f"Conditional edge is misconfigured: {edge_config}")

        def router(state: Dict[str, Any]) -> str:
            actual_value = state.get(variable)

            if operator == "regex":
                if isinstance(actual_value, str) and re.search(str(expected_value), actual_value):
                    return target
                else:
                    return fallback

            if operator not in ConditionalRouter.OPERATORS:
                logger.warning(f"Unknown operator: {operator}, using fallback")
                return fallback

            op_func = ConditionalRouter.OPERATORS[operator]
            try:
                if op_func(actual_value, expected_value):
                    return target
                else:
                    return fallback
            except Exception as e:
                logger.error(f"Router error for operator '{operator}': {e}, using fallback")
                return fallback

        return router


class AgentExecutor:
    ARTIFACT_THRESHOLD_KB = 5.0

    def __init__(
        self,
        agent_config: Dict[str, Any],
        execution_id: str,
        db_session: DBInterface,
        registry: NodeRegistry,
        event_emitter: Optional[Callable] = None,
        cancellation_token: Optional[asyncio.Event] = None,
        artifact_manager: Optional[ArtifactManager] = None,
    ):
        self.agent_config = agent_config
        self.execution_id = execution_id
        self.db = db_session
        self.registry = registry
        self.event_emitter = event_emitter or self._default_emitter
        self.cancellation_token = cancellation_token or asyncio.Event()
        self.artifact_manager = artifact_manager or ArtifactManager()
        self.compiled_graph = None
        self.secrets_in_memory = {}
        logger.info(f"AgentExecutor initialized for execution_id={execution_id}")

    @staticmethod
    def _default_emitter(event_type: str, data: Any = None) -> None:
        logger.debug(f"Event: {event_type} -> {data}")

    def validate(self) -> None:
        logger.info("Validating agent configuration...")
        graph_config = self.agent_config.get("graph")
        if not isinstance(graph_config, dict):
            raise ValueError("Config must contain a 'graph' object.")
        nodes = graph_config.get("nodes")
        edges = graph_config.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("'graph' must contain 'nodes' and 'edges' lists.")
        node_ids = {node["id"] for node in nodes}
        node_types = [node["type"] for node in nodes]
        missing_types = self.registry.validate_node_types(node_types)
        if missing_types:
            raise ValueError(f"Unknown node types: {missing_types}")
        for edge in edges:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                raise ValueError(f"Edge points to non-existent node: {edge}")
            if edge.get("type") == "conditional" and edge.get("fallback_target") not in node_ids:
                raise ValueError(f"Conditional edge has non-existent fallback: {edge}")
        if "input_start" not in node_types:
            raise ValueError("No entry point node (type='input_start') found.")
        logger.info("✓ Validation passed")

    def build_graph(self) -> None:
        logger.info("Building graph...")
        graph = StateGraph(dict)
        graph_config = self.agent_config["graph"]
        nodes = graph_config["nodes"]
        edges = graph_config["edges"]

        for node_config in nodes:
            node_id = node_config["id"]
            node_type = node_config["type"]
            node_func = self.registry.get_implementation(node_type)

            def create_async_wrapper(func, n_id, n_config):
                async def async_node_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                    return await self._node_wrapper(state, node_func=func, node_id=n_id, node_config=n_config)
                return async_node_wrapper

            wrapped_node = create_async_wrapper(node_func, node_id, node_config)
            graph.add_node(node_id, wrapped_node)

            if 'secrets' in node_config:
                self.secrets_in_memory.update(node_config['secrets'])

        for edge_config in edges:
            source = edge_config["source"]
            target = edge_config["target"]
            if edge_config.get("type") == "conditional":
                router = ConditionalRouter.create_router(edge_config)
                graph.add_conditional_edges(source, router)
            else:
                graph.add_edge(source, target)

        entry_point_id = next(n["id"] for n in nodes if n["type"] == "input_start")
        graph.set_entry_point(entry_point_id)
        self.compiled_graph = graph.compile()
        logger.info("✓ Graph compiled successfully")

    async def _node_wrapper(self, state: Dict[str, Any], node_func: Callable, node_id: str, node_config: Dict[str, Any]) -> Dict[str, Any]:
        if self.cancellation_token.is_set():
            logger.warning(f"Node {node_id} cancelled before start.")
            raise asyncio.CancelledError()
        cached_event = await self.db.get_node_event(self.execution_id, node_id)
        if cached_event:
            logger.info(f"Node {node_id} already completed, recovering from cache.")
            cached_output = json.loads(cached_event.get("intermediate_output", "{}"))
            rehydrated = await self._rehydrate_output(cached_output)
            self.event_emitter("node_recovered", {"node_id": node_id})
            return rehydrated

        execution_context = self._build_execution_context(node_config, state)

        try:
            start_event = NodeEvent(execution_id=self.execution_id, node_id=node_id, status="STARTED", timestamp=datetime.utcnow().isoformat())
            await self.db.save_node_event(start_event)
            self.event_emitter("node_start", {"node_id": node_id})

            if asyncio.iscoroutinefunction(node_func):
                result_dict = await node_func(execution_context)
            else:
                loop = asyncio.get_running_loop()
                result_dict = await loop.run_in_executor(None, node_func, execution_context)

            node_result = NodeResult(**result_dict)

        except asyncio.CancelledError:
            logger.warning(f"Node {node_id} was cancelled during execution.")
            raise
        except Exception as e:
            logger.error(f"Node {node_id} failed: {e}", exc_info=True)
            error_event = NodeEvent(execution_id=self.execution_id, node_id=node_id, status="FAILED", timestamp=datetime.utcnow().isoformat(), error_log=traceback.format_exc())
            await self.db.save_node_event(error_event)
            self.event_emitter("node_error", {"node_id": node_id, "error": str(e)})
            raise

        output_for_db = node_result.output
        if self.artifact_manager.should_offload(output_for_db, self.ARTIFACT_THRESHOLD_KB):
            logger.info(f"Output for node {node_id} is large, offloading to artifact.")
            uri = self.artifact_manager.save_content(self.execution_id, node_id, output_for_db)
            output_for_db = {"__ref": uri}

        if node_result.secrets:
            self.secrets_in_memory.update(node_result.secrets)
            logger.debug(f"Node {node_id} updated secrets in memory.")

        final_event = NodeEvent(execution_id=self.execution_id, node_id=node_id, status="COMPLETED", timestamp=datetime.utcnow().isoformat(), intermediate_output=json.dumps(output_for_db, default=str))
        await self.db.save_node_event(final_event)
        self.event_emitter("node_finish", {"node_id": node_id, "status": "COMPLETED"})

        return node_result.output

    def _build_execution_context(self, node_config, state):
        context = node_config.get("config", {}).copy()
        input_map = node_config.get("input_map", {})

        for target_key, source_key in input_map.items():
            if source_key in self.secrets_in_memory:
                context[target_key] = self.secrets_in_memory[source_key]
            elif source_key in state:
                context[target_key] = state[source_key]

        context["cancellation_token"] = self.cancellation_token
        return context

    async def _rehydrate_output(self, cached_output):
        if isinstance(cached_output, dict) and "__ref" in cached_output:
            uri = cached_output["__ref"]
            logger.debug(f"Rehydrating artifact from {uri}")
            try:
                return await asyncio.to_thread(self.artifact_manager.load_content, uri)
            except Exception as e:
                logger.critical(f"Failed to rehydrate artifact {uri}: {e}", exc_info=True)
                raise
        return cached_output

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Starting execution {self.execution_id}...")

        try:
            self.validate()
            self.build_graph()
            current_state = await self._replay_execution(input_data)
            logger.info(f"Invoking compiled graph with replayed state...")
            final_state = await self.compiled_graph.ainvoke(current_state)
            logger.info("✓ Execution completed successfully")
            await self.db.update_execution_status(self.execution_id, "COMPLETED", json.dumps(final_state, default=str))
            self.event_emitter("execution_complete", final_state)
            return final_state

        except asyncio.CancelledError:
            logger.warning("Execution cancelled")
            await self.db.update_execution_status(self.execution_id, "CANCELLED")
            raise
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            await self.db.update_execution_status(self.execution_id, "FAILED", traceback.format_exc())
            raise

    async def _replay_execution(self, input_data):
        logger.info("Replaying execution state from DB...")
        events = await self.db.get_execution_events(self.execution_id)
        current_state = input_data.copy()
        completed_events = [e for e in events if e.get("status") == "COMPLETED"]
        logger.debug(f"Replaying {len(completed_events)} completed node events")

        for event in completed_events:
            intermediate_output = json.loads(event.get("intermediate_output", "{}"))
            rehydrated_output = await self._rehydrate_output(intermediate_output)
            current_state.update(rehydrated_output)

        logger.info(f"Replayed state keys: {list(current_state.keys())}")
        return current_state


if __name__ == "__main__":
    class MockDB(DBInterface):
        def __init__(self):
            self.events: List[Dict] = []

        async def get_node_event(self, execution_id, node_id):
            completed = sorted([e for e in self.events if e["execution_id"] == execution_id and e["node_id"] == node_id and e["status"] == "COMPLETED"], key=lambda x: x["timestamp"], reverse=True)
            return completed[0] if completed else None

        async def save_node_event(self, event: NodeEvent):
            self.events.append(event.dict())

        async def get_execution_events(self, execution_id: str):
            return sorted([e for e in self.events if e["execution_id"] == execution_id], key=lambda x: x["timestamp"])

        async def update_execution_status(self, execution_id, status, final_result=None):
            logger.info(f"Execution {execution_id} status updated to {status}")

    AGENT_CONFIG = {
        "graph": {
            "nodes": [
                {"id": "input_node", "type": "input_start", "config": {}, "input_map": {}},
                {"id": "process_node", "type": "echo", "config": {"prefix": "Processed: "}, "input_map": {"text": "user_input"}},
            ],
            "edges": [
                {"source": "input_node", "target": "process_node", "type": "default"},
            ],
        }
    }

    registry = NodeRegistry()

    async def input_start(context: Dict) -> Dict:
        return NodeResult(status="success", output={"user_input": "Hello, World!"}).dict()

    async def echo(context: Dict) -> Dict:
        prefix = context.get("prefix", "")
        text = context.get("text", "")
        result = {"result": f"{prefix}{text}"}
        return NodeResult(status="success", output=result).dict()

    registry.register("input_start", input_start)
    registry.register("echo", echo)

    async def main():
        db = MockDB()
        executor = AgentExecutor(agent_config=AGENT_CONFIG, execution_id="exec_001", db_session=db, registry=registry)
        final_state = await executor.run({})
        print(f"\nFinal result: {final_state}")

    asyncio.run(main())
