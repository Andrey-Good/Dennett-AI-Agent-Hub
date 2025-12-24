# schemas.py
"""
Data Contracts and Pydantic Models for AgentExecutor V5.6

This module defines strict contracts for:
- Node execution results (NodeResult)
- Execution state (AgentState)
- Database models
- API request/response schemas
"""

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
import json


class NodeResult(BaseModel):
    """
    Strict contract for node output.
    
    Every node MUST return exactly this structure.
    No exceptions - this is the only language nodes speak.
    """
    status: Literal["success", "error", "interrupted"] = Field(
        ..., 
        description="Node execution status"
    )
    output: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node-produced data (can be large)"
    )
    secrets: Optional[Dict[str, str]] = Field(
        default=None,
        description="Updated secrets (stripped before DB storage)"
    )
    artifacts: Optional[List[str]] = Field(
        default=None,
        description="File paths created by node (informational)"
    )

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            bytes: lambda v: f"<binary:{len(v)}bytes>"
        }


class AgentState(BaseModel):
    """
    Strict memory model for agent execution.
    
    Two-zone architecture:
    - vars: Global whiteboard (shared between nodes)
    - nodes: Immutable history of node outputs
    """
    vars: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global variables (whiteboard)"
    )
    nodes: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Node execution history {node_id: {output}}"
    )

    class Config:
        arbitrary_types_allowed = True


class NodeEvent(BaseModel):
    """Database record for a node execution event."""
    execution_id: str
    node_id: str
    status: Literal["STARTED", "COMPLETED", "FAILED", "CANCELLED"]
    timestamp: str
    intermediate_output: Optional[str] = None
    error_log: Optional[str] = None

    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid ISO timestamp: {v}")
        return v


class ExecutionRecord(BaseModel):
    """Database record for an execution."""
    execution_id: str
    agent_id: str
    status: Literal["RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
    started_at: str
    completed_at: Optional[str] = None
    final_result: Optional[str] = None

    @validator('started_at', 'completed_at')
    def validate_timestamps(cls, v):
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid ISO timestamp: {v}")
        return v


class DependencyError(Exception):
    """
    Raised when a node tries to read from a dependency that hasn't executed yet.
    
    This is a LOGICAL error - the graph is misconfigured or has a loop.
    """
    pass


class InputMappingError(Exception):
    """Raised when input mapping references invalid source expressions."""
    pass


# API Schema Models

class ExecutionStartRequest(BaseModel):
    """Request to start a new agent execution."""
    agent_config: Dict[str, Any] = Field(..., description="Full agent configuration")
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial input variables"
    )


class ExecutionStatusResponse(BaseModel):
    """Response with current execution status."""
    execution_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExecutionCancelRequest(BaseModel):
    """Request to cancel a running execution."""
    execution_id: str


class NodeEventResponse(BaseModel):
    """Response with node event details."""
    node_id: str
    status: str
    timestamp: str
    output_size: Optional[int] = None
    has_artifacts: bool = False
