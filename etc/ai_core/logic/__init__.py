# ai_core/logic/__init__.py
"""
AgentExecutor V5.6 - Production-Grade Agent Execution Engine

Complete module for fault-tolerant, non-blocking graph execution with:
- Strict data contracts (NodeResult, AgentState with vars/nodes)
- Fault tolerance via DB replay
- Input/Output mapping (var: and node: prefixes)
- Dependency validation (DependencyError)
- Artifact management (>5KB offloading)
- Security (secret redaction)
- Async-safe execution

Author: SBT Bootcamp
Version: 5.6
"""

# Core execution engine
from .agent_executor import (
    AgentExecutor,
    ArtifactManager,
    NodeRegistry,
    DBInterface,
    ConditionalRouter,
)

# Data models and contracts
from .schemas import (
    NodeResult,
    NodeEvent,
    ExecutionRecord,
    AgentState,
    DependencyError,
    InputMappingError,
    ExecutionStartRequest,
    ExecutionStatusResponse,
    ExecutionCancelRequest,
)

# API layer
from .api import (
    AgentExecutionAPI,
    create_api,
)

# Logging
import logging
logger = logging.getLogger("agent_executor")

__version__ = "5.6"
__author__ = "SBT Bootcamp"

__all__ = [
    # Core
    "AgentExecutor",
    "ArtifactManager",
    "NodeRegistry",
    "DBInterface",
    "ConditionalRouter",
    
    # Schemas
    "NodeResult",
    "NodeEvent",
    "ExecutionRecord",
    "AgentState",
    "DependencyError",
    "InputMappingError",
    
    # API
    "ExecutionStartRequest",
    "ExecutionStatusResponse",
    "ExecutionCancelRequest",
    "AgentExecutionAPI",
    "create_api",
    
    # Logging
    "logger",
]

print(f"✓ AgentExecutor v{__version__} loaded (No Triggers)")
