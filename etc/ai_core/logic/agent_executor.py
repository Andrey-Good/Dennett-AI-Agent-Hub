# agent_executor.py
"""
AgentExecutor V5.6 - Production-Grade Agent Execution Engine

Core responsibilities:
1. Fault Tolerance: Recovery from crashes via DB replay
2. Database Hygiene: Artifact storage for large data (>5KB)
3. Non-Blocking: All I/O in asyncio, sync tasks in executor
4. Security: Secret redaction in logs
5. Strict Contracts: NodeResult, AgentState (vars/nodes)
6. Input/Output Mapping: var: and node: prefix resolution
7. Dependency Validation: DependencyError on unmet dependencies
"""

import asyncio
import json
import logging
import traceback
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from functools import partial

from langgraph.graph import StateGraph
from .schemas import (
    NodeResult, AgentState, NodeEvent, ExecutionRecord,
    DependencyError, InputMappingError
)

logger = logging.getLogger("agent_executor")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ArtifactManager:
    """Manages offloading of large data to disk."""
    
    def __init__(self, base_dir: str = "artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ArtifactManager initialized at {self.base_dir.resolve()}")

    def _ensure_execution_dir(self, execution_id: str) -> Path:
        exec_dir = self.base_dir / execution_id
        exec_dir.mkdir(parents=True, exist_ok=True)
        return exec_dir

    def save_content(self, execution_id: str, node_id: str, data: Any) -> str:
        """Save large data to disk, return artifact URI."""
        exec_dir = self._ensure_execution_dir(execution_id)
        timestamp = datetime.utcnow().isoformat().replace(':', '-').replace('.', '-')
        is_binary = isinstance(data, bytes)
        ext = ".bin" if is_binary else ".json"
        filename = f"{node_id}_{timestamp}{ext}"
        file_path = exec_dir / filename

        try:
            if is_binary:
                with open(file_path, 'wb') as f:
                    f.write(data)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            uri = f"artifact://{execution_id}/{filename}"
            logger.debug(f"Saved artifact: {uri} (size: {file_path.stat().st_size} bytes)")
            return uri
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}", exc_info=True)
            raise

    def load_content(self, uri: str) -> Any:
        """Load data from disk using artifact URI."""
        if not uri.startswith("artifact://"):
            raise ValueError(f"Invalid artifact URI: {uri}")

        path_part = uri[len("artifact://"):]
        file_path = self.base_dir / path_part

        if not file_path.exists():
            raise FileNotFoundError(
                f"CRITICAL: Artifact lost! URI={uri}, Path={file_path.resolve()}"
            )

        try:
            if file_path.suffix == ".json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(file_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to load artifact {uri}: {e}", exc_info=True)
            raise

    def should_offload(self, data: Any, threshold_kb: float = 5.0) -> bool:
        """Check if data exceeds offload threshold."""
        if isinstance(data, bytes):
            return (len(data) / 1024) > threshold_kb
        try:
            size_bytes = len(json.dumps(data, default=str).encode('utf-8'))
            return (size_bytes / 1024) > threshold_kb
        except TypeError:
            return True


class NodeRegistry:
    """Registry of available node implementations."""
    
    def __init__(self):
        self._implementations: Dict[str, Callable] = {}
        logger.info("NodeRegistry initialized")

    def register(self, node_type: str, func: Callable) -> None:
        """Register a node implementation."""
        self._implementations[node_type] = func
        logger.debug(f"Registered node type: {node_type}")

    def get_implementation(self, node_type: str) -> Callable:
        """Get node implementation by type."""
        if node_type not in self._implementations:
            raise ValueError(f"Unknown node type: {node_type}")
        return self._implementations[node_type]

    def validate_node_types(self, node_types: List[str]) -> List[str]:
        """Return list of unknown node types."""
        return [nt for nt in set(node_types) if nt not in self._implementations]


class DBInterface(ABC):
    """Abstract interface for database operations."""
    
    @abstractmethod
    async def get_node_event(self, execution_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get most recent COMPLETED event for a node."""
        pass

    @abstractmethod
    async def save_node_event(self, event: NodeEvent) -> None:
        """Save a node execution event."""
        pass

    @abstractmethod
    async def get_execution_events(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all events for an execution, ordered by timestamp."""
        pass

    @abstractmethod
    async def update_execution_status(
        self, 
        execution_id: str, 
        status: str, 
        final_result: Optional[str] = None
    ) -> None:
        """Update execution status in DB."""
        pass


class ConditionalRouter:
    """Routes graph execution based on state conditions."""
    
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
        """Create a router function for conditional edges."""
        condition = edge_config.get("condition", {})
        variable = condition.get("variable")
        operator = condition.get("operator", "eq")
        expected_value = condition.get("value")
        target = edge_config.get("target")
        fallback = edge_config.get("fallback_target")

        if not all([variable, operator, target, fallback]):
            raise ValueError(f"Conditional edge misconfigured: {edge_config}")

        def router(state: Dict[str, Any]) -> str:
            # Extract value from state (works with vars/nodes structure)
            if "vars" in state:
                actual_value = state["vars"].get(variable)
            else:
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
    """
    Main execution engine for agent graphs.
    
    Architecture:
    - Validates graph on init
    - Builds LangGraph with strict contracts
    - Executes with fault tolerance (replay on restart)
    - Manages state (vars/nodes), artifacts, secrets
    """
    
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
        self.secrets_in_memory: Dict[str, str] = {}
        
        # Build variable index for quick lookup
        self.variable_index: Dict[str, Dict[str, Any]] = {}
        variables = agent_config.get("variables", [])
        for var in variables:
            self.variable_index[var["id"]] = var
        
        logger.info(f"AgentExecutor initialized for execution_id={execution_id}")

    @staticmethod
    def _default_emitter(event_type: str, data: Any = None) -> None:
        logger.debug(f"Event: {event_type} -> {data}")

    def validate(self) -> None:
        """Sanity check: ensure graph structure is valid."""
        logger.info("Validating agent configuration...")
        
        graph_config = self.agent_config.get("graph")
        if not isinstance(graph_config, dict):
            raise ValueError("Config must contain a 'graph' object.")
        
        nodes = graph_config.get("nodes")
        edges = graph_config.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("'graph' must contain 'nodes' and 'edges' lists.")
        
        # Check node existence and types
        node_ids = {node["id"] for node in nodes}
        node_types = [node["type"] for node in nodes]
        missing_types = self.registry.validate_node_types(node_types)
        if missing_types:
            raise ValueError(f"Unknown node types: {missing_types}")
        
        # Check edges reference valid nodes
        for edge in edges:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                raise ValueError(f"Edge points to non-existent node: {edge}")
            if edge.get("type") == "conditional" and edge.get("fallback_target") not in node_ids:
                raise ValueError(f"Conditional edge has non-existent fallback: {edge}")
        
        # Check entry point
        if not any(n["type"] == "input_start" for n in nodes):
            raise ValueError("No entry point node (type='input_start') found.")
        
        # Validate variable references in input_map and output_map
        for node in nodes:
            self._validate_node_mappings(node)
        
        # Validate variable references in edge conditions
        for edge in edges:
            if edge.get("type") == "conditional":
                condition = edge.get("condition", {})
                var_ref = condition.get("variable")
                if var_ref and var_ref not in self.variable_index:
                    raise ValueError(
                        f"Conditional edge references undefined variable: {var_ref}"
                    )
        
        logger.info("✓ Validation passed")

    def _validate_node_mappings(self, node: Dict[str, Any]) -> None:
        """Validate input/output mappings reference valid variables."""
        input_map = node.get("input_map", {})
        output_map = node.get("output_map", {})
        
        for source_key, source_expr in input_map.items():
            if isinstance(source_expr, str):
                # var:name references must exist
                if source_expr.startswith("var:"):
                    var_name = source_expr[4:]
                    if var_name not in self.variable_index:
                        raise ValueError(
                            f"Node {node['id']} input_map references undefined variable: {var_name}"
                        )
                # node:id.field references are checked at runtime (for recovery)
        
        for var_name, _ in output_map.items():
            if var_name not in self.variable_index:
                raise ValueError(
                    f"Node {node['id']} output_map references undefined variable: {var_name}"
                )

    def build_graph(self) -> None:
        """Build LangGraph from config."""
        logger.info("Building graph...")
        graph = StateGraph(dict)
        graph_config = self.agent_config["graph"]
        nodes = graph_config["nodes"]
        edges = graph_config["edges"]

        for node_config in nodes:
            node_id = node_config["id"]
            node_type = node_config["type"]
            node_func = self.registry.get_implementation(node_type)

            # === FIX START: Правильная обертка для асинхронных нод ===
            # Создаем замыкание, чтобы захватить node_func и node_config
            async def node_wrapper(state: Dict[str, Any], _func=node_func, _conf=node_config):
                return await self._node_wrapper(state, node_func=_func, node_config=_conf)
            
            graph.add_node(node_id, node_wrapper)
            # === FIX END ===

            # Load node secrets
            if 'secrets' in node_config:
                self.secrets_in_memory.update(node_config['secrets'])

        # Add edges
        for edge_config in edges:
            source = edge_config["source"]
            target = edge_config["target"]
            if edge_config.get("type") == "conditional":
                router = ConditionalRouter.create_router(edge_config)
                graph.add_conditional_edges(source, router)
            else:
                graph.add_edge(source, target)

        # Set entry point
        entry_point_id = next(n["id"] for n in nodes if n["type"] == "input_start")
        graph.set_entry_point(entry_point_id)
        self.compiled_graph = graph.compile()
        logger.info("✓ Graph compiled successfully")

    async def _node_wrapper(
        self,
        state: Dict[str, Any],
        node_func: Callable,
        node_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Core node execution wrapper (Шаг A-F from ТЗ).
        
        This is the heart of the system - handles all execution logic.
        """
        node_id = node_config["id"]
        
        # ========== Шаг A: Cancellation Check ==========
        if self.cancellation_token.is_set():
            logger.warning(f"Node {node_id} cancelled before start.")
            raise asyncio.CancelledError()

        # ========== Шаг B: Recovery Check (Idempotency) ==========
        cached_event = await self.db.get_node_event(self.execution_id, node_id)
        if cached_event:
            logger.info(f"Node {node_id} already completed, recovering from cache.")
            cached_output = json.loads(cached_event.get("intermediate_output", "{}"))
            rehydrated = await self._rehydrate_output(cached_output)
            # Apply to state (update both vars and nodes)
            state = self._apply_node_output_to_state(state, node_id, rehydrated, node_config)
            self.event_emitter("node_recovered", {"node_id": node_id})
            return state

        # ========== Шаг C: Collect Inputs (Input Mapping) ==========
        execution_context = self._build_execution_context(node_config, state)

        # ========== Шаг D: Execute Node ==========
        try:
            start_event = NodeEvent(
                execution_id=self.execution_id,
                node_id=node_id,
                status="STARTED",
                timestamp=datetime.utcnow().isoformat()
            )
            await self.db.save_node_event(start_event)
            self.event_emitter("node_start", {"node_id": node_id})

            # Run sync or async node
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
            error_event = NodeEvent(
                execution_id=self.execution_id,
                node_id=node_id,
                status="FAILED",
                timestamp=datetime.utcnow().isoformat(),
                error_log=traceback.format_exc()
            )
            await self.db.save_node_event(error_event)
            self.event_emitter("node_error", {"node_id": node_id, "error": str(e)})
            raise

        # ========== Шаг E: Process Output & Save ==========
        # Handle artifacts
        output_for_db = node_result.output
        if self.artifact_manager.should_offload(output_for_db, self.ARTIFACT_THRESHOLD_KB):
            logger.info(f"Output for node {node_id} is large, offloading to artifact.")
            uri = self.artifact_manager.save_content(self.execution_id, node_id, output_for_db)
            output_for_db = {"__ref": uri}

        # Handle secrets (redact before DB)
        if node_result.secrets:
            self.secrets_in_memory.update(node_result.secrets)
            logger.debug(f"Node {node_id} updated secrets in memory.")

        # Save to DB
        final_event = NodeEvent(
            execution_id=self.execution_id,
            node_id=node_id,
            status="COMPLETED",
            timestamp=datetime.utcnow().isoformat(),
            intermediate_output=json.dumps(output_for_db, default=str)
        )
        await self.db.save_node_event(final_event)
        self.event_emitter("node_finish", {"node_id": node_id, "status": "COMPLETED"})

        # ========== Шаг F: Update State & Return ==========
        state = self._apply_node_output_to_state(state, node_id, node_result.output, node_config)
        return state

    def _build_execution_context(self, node_config: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Шаг C: Assemble input parameters for node.
        
        Implements Input Mapping logic:
        - Collect static config
        - Overlay with input_map (var: and node: resolution)
        - Add secrets
        """
        context = node_config.get("config", {}).copy()
        input_map = node_config.get("input_map", {})

        # Resolve input mapping
        for target_key, source_expr in input_map.items():
            try:
                value = self._resolve_slot_from_state(state, source_expr)
                if value is None and source_expr.startswith("node:"):
                    # Node dependency not met
                    raise DependencyError(
                        f"Node input requires '{source_expr}' but dependency not executed yet"
                    )
                context[target_key] = value
            except DependencyError:
                raise
            except Exception as e:
                logger.error(f"Failed to resolve input '{source_expr}': {e}")
                raise InputMappingError(f"Invalid input_map expression: {source_expr}")

        # Add secrets
        for secret_key, secret_name in node_config.get("secrets", {}).items():
            if secret_name in self.secrets_in_memory:
                context[secret_key] = self.secrets_in_memory[secret_name]

        # Add cancellation token
        context["cancellation_token"] = self.cancellation_token
        return context

    def _resolve_slot_from_state(self, state: Dict[str, Any], source_expr: str) -> Any:
        """
        Resolve var: and node: references from state.
        
        - var:name → state['vars'][name]
        - node:id.field.subfield → state['nodes'][id]['field']['subfield']
        
        Returns None if not found (doesn't raise for var: misses).
        Raises DependencyError if node not executed for node: references.
        """
        if source_expr.startswith("var:"):
            var_name = source_expr[4:]
            vars_dict = state.get("vars", {})
            return vars_dict.get(var_name)

        elif source_expr.startswith("node:"):
            path = source_expr[5:]  # "id.field.subfield"
            parts = path.split(".")
            node_id = parts[0]
            
            nodes_dict = state.get("nodes", {})
            if node_id not in nodes_dict:
                raise DependencyError(
                    f"Node '{node_id}' has not been executed yet (required by {source_expr})"
                )
            
            value = nodes_dict[node_id]
            for field in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(field)
                else:
                    return None
            return value

        else:
            raise InputMappingError(
                f"Unsupported input_map source expression: '{source_expr}'. "
                f"Must start with 'var:' or 'node:'"
            )

    def _apply_node_output_to_state(
        self,
        state: Dict[str, Any],
        node_id: str,
        output: Dict[str, Any],
        node_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Шаг F + Recovery: Apply node output to state.
        
        - Store output in state['nodes'][node_id]
        - Apply output_map to store values in state['vars']
        - Handle artifact storage (if variable.storage == "artifact")
        """
        # Ensure state has correct structure
        if "vars" not in state:
            state["vars"] = {}
        if "nodes" not in state:
            state["nodes"] = {}

        # Store full output in nodes history
        state["nodes"][node_id] = output

        # Apply output_map
        output_map = node_config.get("output_map", {})
        for var_name, output_key in output_map.items():
            value = output.get(output_key)
            
            # Check if variable should be stored as artifact
            var_config = self.variable_index.get(var_name, {})
            storage = var_config.get("storage", "inline")
            
            if storage == "artifact" and self.artifact_manager.should_offload(value):
                # Save to disk, store reference
                uri = self.artifact_manager.save_content(self.execution_id, node_id, value)
                state["vars"][var_name] = {"__ref": uri}
            else:
                # Store inline
                state["vars"][var_name] = value

        return state

    async def _rehydrate_output(self, cached_output: Dict[str, Any]) -> Dict[str, Any]:
        """Load artifact if output contains __ref."""
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
        """
        Execute the agent graph.
        
        1. Validate configuration
        2. Build graph
        3. Replay previous execution (if exists)
        4. Run graph with fault tolerance
        5. Return final state
        """
        logger.info(f"Starting execution {self.execution_id}...")

        try:
            self.validate()
            self.build_graph()
            
            # Prepare initial state
            current_state = await self._replay_execution(input_data)
            
            # Run graph
            logger.info("Invoking compiled graph...")
            final_state = await self.compiled_graph.ainvoke(current_state)
            
            logger.info("✓ Execution completed successfully")
            await self.db.update_execution_status(
                self.execution_id,
                "COMPLETED",
                json.dumps(final_state, default=str)
            )
            self.event_emitter("execution_complete", final_state)
            return final_state

        except asyncio.CancelledError:
            logger.warning("Execution cancelled")
            await self.db.update_execution_status(self.execution_id, "CANCELLED")
            raise
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            await self.db.update_execution_status(
                self.execution_id,
                "FAILED",
                traceback.format_exc()
            )
            raise

    async def _replay_execution(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recovery logic: Reconstruct state from DB.
        
        1. Load all COMPLETED events from DB
        2. Rehydrate artifacts
        3. Apply outputs to state using same logic as live execution
        """
        logger.info("Replaying execution state from DB...")
        events = await self.db.get_execution_events(self.execution_id)
        
        # Initialize state with input
        current_state = {
            "vars": input_data.copy(),
            "nodes": {}
        }
        
        completed_events = [e for e in events if e.get("status") == "COMPLETED"]
        logger.debug(f"Replaying {len(completed_events)} completed node events")

        for event in completed_events:
            node_id = event["node_id"]
            intermediate_output = json.loads(event.get("intermediate_output", "{}"))
            rehydrated_output = await self._rehydrate_output(intermediate_output)
            
            # Find node config to apply output_map correctly
            node_config = next(
                (n for n in self.agent_config["graph"]["nodes"] if n["id"] == node_id),
                {"id": node_id, "output_map": {}}
            )
            
            # Apply output using same logic as live execution
            current_state = self._apply_node_output_to_state(
                current_state, node_id, rehydrated_output, node_config
            )

        logger.info(f"Replayed state - vars keys: {list(current_state['vars'].keys())}, "
                   f"nodes: {list(current_state['nodes'].keys())}")
        return current_state
