# apps/ai_core/ai_core/api/agents_api.py
"""
FastAPI endpoints for agent management with database persistence.

This module provides REST API endpoints for CRUD operations on agents,
agent runs, and test cases using the database repositories.

Routes:
    GET  /agents              - List all agents
    POST /agents              - Create a new agent
    GET  /agents/{agent_id}   - Get agent details
    PUT  /agents/{agent_id}   - Update agent
    DELETE /agents/{agent_id} - Delete agent
    
    GET  /agents/{agent_id}/runs      - List agent runs
    POST /agents/{agent_id}/runs      - Create agent run
    GET  /agents/{agent_id}/runs/{run_id} - Get run details
    
    GET  /agents/{agent_id}/test-cases      - List test cases
    POST /agents/{agent_id}/test-cases      - Create test case
    DELETE /agents/{agent_id}/test-cases/{case_id} - Delete test case
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from apps.ai_core.ai_core.db.session import get_session
from apps.ai_core.ai_core.db.repositories import (
    AgentRepository, AgentRunRepository, AgentTestCaseRepository
)
from apps.ai_core.ai_core.db.orm_models import Agent, AgentRun, AgentTestCase

# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class AgentCreate(BaseModel):
    """Request model for creating an agent."""
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "News Aggregator",
                "description": "Aggregates news from multiple sources",
                "tags": ["news", "aggregation"]
            }
        }


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Agent Name",
                "tags": ["updated", "tag"]
            }
        }


class AgentResponse(BaseModel):
    """Response model for agent data."""
    id: str = Field(..., description="Agent UUID")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    tags: List[str] = Field(default_factory=list, description="Agent tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    modified_at: datetime = Field(..., description="Last modification timestamp")
    
    class Config:
        from_attributes = True


class AgentRunCreate(BaseModel):
    """Request model for creating an agent run."""
    trigger_type: str = Field(..., description="How run was triggered")
    status: Optional[str] = Field("pending", description="Initial status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "trigger_type": "manual",
                "status": "pending"
            }
        }


class AgentRunUpdate(BaseModel):
    """Request model for updating a run."""
    status: str = Field(..., description="New status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed"
            }
        }


class AgentRunResponse(BaseModel):
    """Response model for agent run data."""
    run_id: str = Field(..., description="Run UUID")
    agent_id: str = Field(..., description="Agent UUID")
    status: str = Field(..., description="Run status")
    priority: int = Field(..., description="Task priority")
    trigger_type: str = Field(..., description="Trigger type")
    start_time: datetime = Field(..., description="Start timestamp")
    end_time: Optional[datetime] = Field(None, description="End timestamp")
    error_message: Optional[str] = Field(None, description="Error message")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate run duration."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    class Config:
        from_attributes = True


class AgentTestCaseCreate(BaseModel):
    """Request model for creating a test case."""
    node_id: str = Field(..., description="Node ID for state insertion")
    name: str = Field(..., min_length=1, description="Test case name")
    initial_state: Dict[str, Any] = Field(..., description="Initial state object")
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node_001",
                "name": "Test empty input",
                "initial_state": {
                    "input": "",
                    "expected_output": "Error message"
                }
            }
        }


class AgentTestCaseResponse(BaseModel):
    """Response model for test case data."""
    case_id: str = Field(..., description="Test case UUID")
    agent_id: str = Field(..., description="Agent UUID")
    node_id: str = Field(..., description="Node ID")
    name: str = Field(..., description="Test case name")
    initial_state: Dict[str, Any] = Field(..., description="Initial state")
    
    class Config:
        from_attributes = True


class AgentStatistics(BaseModel):
    """Response model for agent run statistics."""
    agent_id: str = Field(..., description="Agent UUID")
    total_runs: int = Field(..., description="Total number of runs")
    completed: int = Field(..., description="Completed runs")
    failed: int = Field(..., description="Failed runs")
    pending: int = Field(..., description="Pending runs")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_duration_seconds: Optional[float] = Field(None, description="Average duration")


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}}
)


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.get("", response_model=List[AgentResponse])
def list_agents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """
    List all agents with pagination.
    
    Query Parameters:
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)
    """
    repo = AgentRepository(session)
    agents = repo.list_all(limit=limit, offset=offset)
    return agents


@router.post("", response_model=AgentResponse, status_code=201)
def create_agent(
    agent: AgentCreate,
    session: Session = Depends(get_session)
):
    """Create a new agent."""
    repo = AgentRepository(session)
    created = repo.create(
        name=agent.name,
        description=agent.description,
        tags=agent.tags
    )
    return created


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """Get agent details by ID."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    update: AgentUpdate,
    session: Session = Depends(get_session)
):
    """Update agent properties."""
    repo = AgentRepository(session)
    
    # Prepare update data (exclude None values)
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    updated = repo.update(agent_id, **update_data)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return updated


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """Delete an agent and all associated data."""
    repo = AgentRepository(session)
    
    if not repo.delete(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")


# ============================================================================
# Agent Run Endpoints
# ============================================================================

@router.get("/{agent_id}/runs", response_model=List[AgentRunResponse])
def list_agent_runs(
    agent_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """List all runs for a specific agent."""
    # Verify agent exists
    agent_repo = AgentRepository(session)
    if not agent_repo.get_by_id(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    run_repo = AgentRunRepository(session)
    runs = run_repo.list_by_agent(agent_id, limit=limit, offset=offset)
    return runs


@router.post("/{agent_id}/runs", response_model=AgentRunResponse, status_code=201)
def create_agent_run(
    agent_id: str,
    run: AgentRunCreate,
    session: Session = Depends(get_session)
):
    """Create a new run for an agent."""
    from apps.ai_core.ai_core.logic.priority_policy import get_priority_policy, TaskSource

    trigger_to_source = {
        "manual": TaskSource.MANUAL_RUN,
        "schedule": TaskSource.TRIGGER,
        "webhook": TaskSource.TRIGGER,
        "file_system": TaskSource.TRIGGER,
        "chat": TaskSource.CHAT,
        "chat_agent": TaskSource.CHAT_AGENT
    }

    policy = get_priority_policy()
    task_source = trigger_to_source.get(run.trigger_type, TaskSource.TRIGGER)
    priority = policy.assign_priority(
        source=task_source,
        parent_priority=None
    )

    run_repo = AgentRunRepository(session)
    
    try:
        created = run_repo.create(
            agent_id=agent_id,
            trigger_type=run.trigger_type,
            status=run.status,
            priority=priority
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_id}/runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(
    agent_id: str,
    run_id: str,
    session: Session = Depends(get_session)
):
    """Get details of a specific run."""
    run_repo = AgentRunRepository(session)
    run = run_repo.get_by_id(run_id)
    
    if not run or run.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return run


@router.put("/{agent_id}/runs/{run_id}", response_model=AgentRunResponse)
def update_agent_run(
    agent_id: str,
    run_id: str,
    update: AgentRunUpdate,
    session: Session = Depends(get_session)
):
    """Update run status."""
    run_repo = AgentRunRepository(session)
    
    updated = run_repo.update_status(
        run_id,
        status=update.status,
        error_message=update.error_message
    )
    
    if not updated or updated.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return updated


@router.get("/{agent_id}/statistics", response_model=AgentStatistics)
def get_agent_statistics(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """Get statistics for an agent's runs."""
    agent_repo = AgentRepository(session)
    if not agent_repo.get_by_id(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    run_repo = AgentRunRepository(session)
    stats = run_repo.get_statistics(agent_id)
    
    return AgentStatistics(agent_id=agent_id, **stats)


# ============================================================================
# Agent Test Case Endpoints
# ============================================================================

@router.get("/{agent_id}/test-cases", response_model=List[AgentTestCaseResponse])
def list_test_cases(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """List all test cases for an agent."""
    agent_repo = AgentRepository(session)
    if not agent_repo.get_by_id(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    test_repo = AgentTestCaseRepository(session)
    test_cases = test_repo.list_by_agent(agent_id)
    return test_cases


@router.post("/{agent_id}/test-cases", response_model=AgentTestCaseResponse, status_code=201)
def create_test_case(
    agent_id: str,
    test_case: AgentTestCaseCreate,
    session: Session = Depends(get_session)
):
    """Create a new test case for an agent."""
    test_repo = AgentTestCaseRepository(session)
    
    try:
        created = test_repo.create(
            agent_id=agent_id,
            node_id=test_case.node_id,
            name=test_case.name,
            initial_state=test_case.initial_state
        )
        return created
    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg:
            raise HTTPException(status_code=409, detail=error_msg)
        else:
            raise HTTPException(status_code=404, detail=error_msg)


@router.delete("/{agent_id}/test-cases/{case_id}", status_code=204)
def delete_test_case(
    agent_id: str,
    case_id: str,
    session: Session = Depends(get_session)
):
    """Delete a test case."""
    test_repo = AgentTestCaseRepository(session)
    test_case = test_repo.get_by_id(case_id)
    
    if not test_case or test_case.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    test_repo.delete(case_id)
