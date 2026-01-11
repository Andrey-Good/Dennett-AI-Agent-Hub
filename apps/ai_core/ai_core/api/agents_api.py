# apps/ai_core/ai_core/api/agents_api.py
"""
FastAPI endpoints for agent management with database persistence (v5.0).

This module provides REST API endpoints for CRUD operations on agents,
agent runs, drafts, and test cases using the database repositories.

Routes:
    GET  /agents              - List all agents
    POST /agents              - Create a new agent
    GET  /agents/{agent_id}   - Get agent details
    PUT  /agents/{agent_id}   - Update agent
    DELETE /agents/{agent_id} - Soft delete agent

    POST /agents/{agent_id}/activate   - Activate agent triggers
    POST /agents/{agent_id}/deactivate - Deactivate agent triggers

    GET  /agents/{agent_id}/versions   - List live + all drafts

    POST   /agents/{agent_id}/drafts              - Create draft
    GET    /agents/{agent_id}/drafts/{draft_id}   - Get draft content
    PUT    /agents/{agent_id}/drafts/{draft_id}   - Update draft (autosave)
    DELETE /agents/{agent_id}/drafts/{draft_id}   - Delete draft
    POST   /agents/{agent_id}/drafts/{draft_id}/deploy - Deploy draft

    GET  /agents/{agent_id}/runs      - List agent runs
    POST /agents/{agent_id}/runs      - Create agent run
    GET  /agents/{agent_id}/runs/{run_id} - Get run details

    GET  /agents/{agent_id}/test-cases      - List test cases
    POST /agents/{agent_id}/test-cases      - Create test case
    DELETE /agents/{agent_id}/test-cases/{case_id} - Delete test case
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

from apps.ai_core.ai_core.db.session import get_session
from apps.ai_core.ai_core.db.repositories import (
    AgentRepository, AgentRunRepository, AgentTestCaseRepository, AgentDraftRepository
)
from apps.ai_core.ai_core.db.orm_models import Agent, AgentRun, AgentTestCase, AgentDraft
from apps.ai_core.ai_core.logic.atomic_write import atomic_write_json, read_json_file
from apps.ai_core.ai_core.logic.trigger_manager import get_trigger_manager
from apps.ai_core.ai_core.logic.filesystem_manager import file_system_manager

try:
    import uuid6
    def uuid7str() -> str:
        return str(uuid6.uuid7())
except ImportError:
    import uuid
    def uuid7str() -> str:
        return str(uuid.uuid4())

logger = logging.getLogger(__name__)

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
    """Response model for agent data (v5.0)."""
    id: str = Field(..., description="Agent UUID")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    tags: List[str] = Field(default_factory=list, description="Agent tags")
    version: int = Field(..., description="Current version number")
    is_active: bool = Field(..., description="Whether triggers are loaded")
    updated_at: datetime = Field(..., description="Last modification timestamp")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_agent(cls, agent: Agent) -> "AgentResponse":
        """Create response from ORM model."""
        return cls(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            tags=agent.get_tags() if isinstance(agent.tags, str) else (agent.tags or []),
            version=agent.version,
            is_active=agent.is_active == 1,
            updated_at=agent.modified_at
        )


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
# v5.0 Draft/Version Models
# ============================================================================

class DraftCreate(BaseModel):
    """Request model for creating a draft."""
    name: str = Field(..., min_length=1, max_length=255, description="Draft name")
    source: str = Field(..., description="Source: 'live' or draft UUID")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Experiment with RAG",
                "source": "live"
            }
        }


class DraftResponse(BaseModel):
    """Response model for draft metadata."""
    draft_id: str = Field(..., description="Draft UUID")
    name: str = Field(..., description="Draft name")
    base_version: int = Field(..., description="Base version number")
    updated_at: str = Field(..., description="Last update timestamp")
    type: str = Field(default="draft", description="Version type")


class DraftContentResponse(BaseModel):
    """Response model for draft content."""
    updated_at: str = Field(..., description="Last update timestamp")
    graph: Dict[str, Any] = Field(..., description="Full graph JSON")


class DraftUpdate(BaseModel):
    """Request model for updating a draft (autosave)."""
    name: Optional[str] = Field(None, description="New name")
    expected_updated_at: Optional[str] = Field(None, description="For optimistic locking")
    graph: Dict[str, Any] = Field(..., description="Graph JSON to save")


class VersionItem(BaseModel):
    """A version item in the versions list."""
    id: str = Field(..., description="ID (agent_id for live, draft_id for drafts)")
    name: str = Field(..., description="Name")
    version: Optional[int] = Field(None, description="Version number (live only)")
    base_version: Optional[int] = Field(None, description="Base version (drafts only)")
    updated_at: str = Field(..., description="Last update timestamp")
    is_active: Optional[bool] = Field(None, description="Is active (live only)")
    type: str = Field(..., description="'live' or 'draft'")


class VersionsResponse(BaseModel):
    """Response model for versions list."""
    versions: List[VersionItem] = Field(..., description="List of versions")


class DeployResponse(BaseModel):
    """Response model for deploy operation."""
    status: str = Field(..., description="Deploy status")
    new_version: int = Field(..., description="New version number")


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str = Field(..., description="Operation status")


class AgentCreatedResponse(BaseModel):
    """Response for agent creation."""
    agent_id: str = Field(..., description="Created agent UUID")
    status: str = Field(default="created", description="Status")


# ============================================================================
# Helper Functions
# ============================================================================

def get_data_root() -> str:
    """Get the DATA_ROOT path for agent files."""
    return str(file_system_manager.get_agents_dir())


def get_default_graph() -> Dict[str, Any]:
    """Get default graph structure for new agents."""
    return {
        "nodes": [
            {"id": "start", "type": "start", "data": {}},
            {"id": "end", "type": "end", "data": {}}
        ],
        "edges": [
            {"source": "start", "target": "end"}
        ],
        "triggers": [],
        "permissions": {}
    }


def check_agent_not_pending(agent: Agent) -> None:
    """Raise 409 if agent is pending deletion."""
    if agent.deletion_status == 'PENDING':
        raise HTTPException(
            status_code=409,
            detail="Agent is marked for deletion"
        )


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
    List all agents with pagination (v5.0).

    Only returns agents with deletion_status='NONE'.

    Query Parameters:
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)
    """
    repo = AgentRepository(session)
    agents = repo.list_all(limit=limit, offset=offset)
    return [AgentResponse.from_orm_agent(a) for a in agents]


@router.post("", response_model=AgentCreatedResponse, status_code=201)
def create_agent(
    agent: AgentCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new agent (v5.0).

    Creates agent record and writes default graph JSON to disk.
    """
    # Generate UUIDv7 for the agent
    agent_id = uuid7str()

    # Prepare file path (relative to DATA_ROOT)
    relative_path = f"{agent_id}/v1.json"
    absolute_path = os.path.join(get_data_root(), relative_path)

    # Write default graph to disk
    default_graph = get_default_graph()
    atomic_write_json(absolute_path, default_graph)

    # Create agent in database
    repo = AgentRepository(session)
    created = repo.create(
        name=agent.name,
        description=agent.description,
        tags=agent.tags,
        agent_id=agent_id,
        version=1,
        is_active=0,
        deletion_status='NONE',
        file_path=relative_path
    )

    logger.info(f"Created agent {agent_id} with file {relative_path}")
    return AgentCreatedResponse(agent_id=created.id, status="created")


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

    return AgentResponse.from_orm_agent(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    update: AgentUpdate,
    session: Session = Depends(get_session)
):
    """Update agent properties (name, description, tags only)."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    check_agent_not_pending(agent)

    # Prepare update data (exclude None values)
    update_data = {k: v for k, v in update.dict().items() if v is not None}

    updated = repo.update(agent_id, **update_data)

    return AgentResponse.from_orm_agent(updated)


@router.delete("/{agent_id}", response_model=StatusResponse)
def delete_agent(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Soft delete an agent (v5.0).

    Marks agent for deletion (deletion_status='PENDING').
    Physical deletion is performed by the GarbageCollector worker.
    """
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Unregister triggers
    trigger_manager = get_trigger_manager()
    trigger_manager.unregister_triggers_for_agent(agent_id)

    # Mark for deletion
    repo.mark_for_deletion(agent_id)

    logger.info(f"Marked agent {agent_id} for deletion")
    return StatusResponse(status="marked_for_deletion")


# ============================================================================
# Agent Activation Endpoints (v5.0)
# ============================================================================

@router.post("/{agent_id}/activate", response_model=StatusResponse)
def activate_agent(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Activate an agent (load triggers).

    Reads the live JSON file and registers all triggers.
    """
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    check_agent_not_pending(agent)

    trigger_manager = get_trigger_manager()

    # Clear any existing triggers first
    trigger_manager.unregister_triggers_for_agent(agent_id)

    # Read live JSON and register triggers
    if agent.file_path:
        try:
            absolute_path = os.path.join(get_data_root(), agent.file_path)
            graph_data = read_json_file(absolute_path)
            triggers = graph_data.get('triggers', [])

            for trigger_config in triggers:
                trigger_manager.register_trigger(agent_id, trigger_config)
        except FileNotFoundError:
            logger.warning(f"Agent file not found: {agent.file_path}")
        except Exception as e:
            logger.error(f"Error reading agent file: {e}")

    # Update agent status
    repo.activate(agent_id)

    return StatusResponse(status="active")


@router.post("/{agent_id}/deactivate", response_model=StatusResponse)
def deactivate_agent(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Deactivate an agent (unload triggers).
    """
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    check_agent_not_pending(agent)

    # Unregister triggers
    trigger_manager = get_trigger_manager()
    trigger_manager.unregister_triggers_for_agent(agent_id)

    # Update agent status
    repo.deactivate(agent_id)

    return StatusResponse(status="inactive")


# ============================================================================
# Versions & Drafts Endpoints (v5.0)
# ============================================================================

@router.get("/{agent_id}/versions", response_model=VersionsResponse)
def list_versions(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Get all versions of an agent (live + drafts).
    """
    agent_repo = AgentRepository(session)
    agent = agent_repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    versions = []

    # Add live version
    live_item = VersionItem(
        id=agent.id,
        name=agent.name,
        version=agent.version,
        base_version=None,
        updated_at=agent.modified_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
        is_active=agent.is_active == 1,
        type="live"
    )
    versions.append(live_item)

    # Add drafts
    draft_repo = AgentDraftRepository(session)
    drafts = draft_repo.list_by_agent(agent_id)

    for draft in drafts:
        draft_item = VersionItem(
            id=draft.draft_id,
            name=draft.name,
            version=None,
            base_version=draft.base_version,
            updated_at=draft.updated_at,
            is_active=None,
            type="draft"
        )
        versions.append(draft_item)

    return VersionsResponse(versions=versions)


@router.post("/{agent_id}/drafts", response_model=DraftResponse, status_code=201)
def create_draft(
    agent_id: str,
    draft_request: DraftCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new draft from live or another draft.
    """
    agent_repo = AgentRepository(session)
    agent = agent_repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    check_agent_not_pending(agent)

    draft_repo = AgentDraftRepository(session)

    # Resolve source
    source = draft_request.source
    if source == "live":
        # Source is live version
        source_file_path = agent.file_path
        base_version = agent.version
    else:
        # Source is another draft
        source_draft = draft_repo.get_by_id_and_agent(source, agent_id)
        if not source_draft:
            raise HTTPException(status_code=404, detail="Source draft not found")
        source_file_path = source_draft.file_path
        base_version = source_draft.base_version

    if not source_file_path:
        raise HTTPException(status_code=400, detail="Source has no file")

    # Read source JSON
    try:
        source_absolute = os.path.join(get_data_root(), source_file_path)
        source_data = read_json_file(source_absolute)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source file not found")

    # Generate new draft ID and path
    new_draft_id = uuid7str()
    relative_path = f"{agent_id}/drafts/{new_draft_id}.json"
    absolute_path = os.path.join(get_data_root(), relative_path)

    # Write draft file
    atomic_write_json(absolute_path, source_data)

    # Create draft record
    draft = draft_repo.create(
        agent_id=agent_id,
        name=draft_request.name,
        file_path=relative_path,
        base_version=base_version,
        draft_id=new_draft_id
    )

    return DraftResponse(
        draft_id=draft.draft_id,
        name=draft.name,
        base_version=draft.base_version,
        updated_at=draft.updated_at,
        type="draft"
    )


@router.get("/{agent_id}/drafts/{draft_id}", response_model=DraftContentResponse)
def get_draft(
    agent_id: str,
    draft_id: str,
    session: Session = Depends(get_session)
):
    """
    Get draft content for editing.
    """
    draft_repo = AgentDraftRepository(session)
    draft = draft_repo.get_by_id_and_agent(draft_id, agent_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Read file
    try:
        absolute_path = os.path.join(get_data_root(), draft.file_path)
        graph_data = read_json_file(absolute_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft file not found")

    return DraftContentResponse(
        updated_at=draft.updated_at,
        graph=graph_data
    )


@router.put("/{agent_id}/drafts/{draft_id}", response_model=StatusResponse)
def update_draft(
    agent_id: str,
    draft_id: str,
    update: DraftUpdate,
    session: Session = Depends(get_session)
):
    """
    Update draft content (autosave).

    Supports optimistic locking via expected_updated_at.
    """
    draft_repo = AgentDraftRepository(session)
    draft = draft_repo.get_by_id_and_agent(draft_id, agent_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Optimistic locking check
    if update.expected_updated_at and draft.updated_at != update.expected_updated_at:
        raise HTTPException(
            status_code=409,
            detail="Conflict: draft was modified by another process"
        )

    # Write graph to file
    absolute_path = os.path.join(get_data_root(), draft.file_path)
    atomic_write_json(absolute_path, update.graph)

    # Update draft record
    try:
        updated_draft = draft_repo.update_with_lock_check(
            draft_id=draft_id,
            agent_id=agent_id,
            expected_updated_at=update.expected_updated_at,
            name=update.name
        )
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail="Conflict: draft was modified by another process"
        )

    return StatusResponse(status="saved")


@router.delete("/{agent_id}/drafts/{draft_id}", response_model=StatusResponse)
def delete_draft(
    agent_id: str,
    draft_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete a draft.
    """
    draft_repo = AgentDraftRepository(session)
    draft = draft_repo.get_by_id_and_agent(draft_id, agent_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    file_path = draft.file_path

    # Delete from database
    draft_repo.delete(draft_id)

    # Delete file (best-effort)
    try:
        absolute_path = os.path.join(get_data_root(), file_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
    except OSError as e:
        logger.warning(f"Failed to delete draft file {file_path}: {e}")

    return StatusResponse(status="deleted")


@router.post("/{agent_id}/drafts/{draft_id}/deploy", response_model=DeployResponse)
def deploy_draft(
    agent_id: str,
    draft_id: str,
    session: Session = Depends(get_session)
):
    """
    Deploy a draft as the new live version.
    """
    agent_repo = AgentRepository(session)
    agent = agent_repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    check_agent_not_pending(agent)

    draft_repo = AgentDraftRepository(session)
    draft = draft_repo.get_by_id_and_agent(draft_id, agent_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Check for version conflict
    if draft.base_version != agent.version:
        raise HTTPException(
            status_code=409,
            detail=f"Conflict: draft is based on v{draft.base_version}, "
                   f"but current version is v{agent.version}"
        )

    # Read and validate draft
    try:
        draft_absolute = os.path.join(get_data_root(), draft.file_path)
        graph_data = read_json_file(draft_absolute)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft file not found")

    # Validate triggers config
    trigger_manager = get_trigger_manager()
    triggers = graph_data.get('triggers', [])
    is_valid, error_msg = trigger_manager.validate_triggers_config(triggers)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid triggers: {error_msg}")

    # Prepare new version
    new_version = agent.version + 1
    new_relative_path = f"{agent_id}/v{new_version}.json"
    new_absolute_path = os.path.join(get_data_root(), new_relative_path)

    # Write new version file (BEFORE transaction)
    atomic_write_json(new_absolute_path, graph_data)

    # Update database (transaction)
    try:
        # Update agent - initially set is_active=0
        agent.version = new_version
        agent.file_path = new_relative_path
        agent.is_active = 0
        agent.modified_at = datetime.utcnow()
        session.commit()

        # Delete draft record
        draft_repo.delete(draft_id)

    except Exception as e:
        session.rollback()
        # Clean up new version file
        try:
            if os.path.exists(new_absolute_path):
                os.remove(new_absolute_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Deploy failed: {e}")

    # Rotate triggers (AFTER commit)
    try:
        trigger_manager.unregister_triggers_for_agent(agent_id)
        for trigger_config in triggers:
            trigger_manager.register_trigger(agent_id, trigger_config)

        # Set is_active=1 if triggers registered successfully
        agent_repo.activate(agent_id)

    except Exception as e:
        logger.error(f"Failed to activate triggers for agent {agent_id}: {e}")
        # Agent remains is_active=0 but deploy succeeded
        return DeployResponse(status="deployed_inactive", new_version=new_version)

    # Delete draft file (best-effort)
    try:
        if os.path.exists(draft_absolute):
            os.remove(draft_absolute)
    except OSError as e:
        logger.warning(f"Failed to delete draft file: {e}")

    logger.info(f"Deployed agent {agent_id} to v{new_version}")
    return DeployResponse(status="deployed", new_version=new_version)


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
