# apps/ai_core/ai_core/api/triggers_api.py
"""
FastAPI endpoints for trigger management.

This module provides REST API endpoints for managing trigger instances
via the TriggerManager.

Routes:
    GET  /triggers                      - List all triggers
    GET  /triggers/{trigger_instance_id} - Get trigger details

    PUT  /agents/{agent_id}/triggers    - Set agent triggers (idempotent)
    GET  /agents/{agent_id}/triggers    - List agent triggers
    DELETE /agents/{agent_id}/triggers  - Delete all agent triggers
    POST /agents/{agent_id}/triggers/enable  - Enable all agent triggers
    POST /agents/{agent_id}/triggers/disable - Disable all agent triggers
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

try:
    from apps.ai_core.ai_core.db.session import get_session
    from apps.ai_core.ai_core.db.repositories import AgentRepository
    from apps.ai_core.ai_core.logic.trigger_manager import (
        get_trigger_manager,
        TriggerInstanceResponse,
        SetAgentTriggersRequest,
        SetAgentTriggersResponse,
        DeleteAgentTriggersResponse,
        SetAgentTriggersEnabledResponse,
    )
except ModuleNotFoundError:
    from ai_core.db.session import get_session
    from ai_core.db.repositories import AgentRepository
    from ai_core.logic.trigger_manager import (
        get_trigger_manager,
        TriggerInstanceResponse,
        SetAgentTriggersRequest,
        SetAgentTriggersResponse,
        DeleteAgentTriggersResponse,
        SetAgentTriggersEnabledResponse,
    )

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/triggers",
    tags=["triggers"],
    responses={404: {"description": "Not found"}}
)

# Also create a router for agent-scoped trigger operations
agent_triggers_router = APIRouter(
    prefix="/agents",
    tags=["triggers"],
    responses={404: {"description": "Not found"}}
)


# ============================================================================
# Helper Functions
# ============================================================================

def _check_agent_exists(agent_id: str, session: Session) -> None:
    """Check if agent exists, raise 404 if not."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    if agent.deletion_status == 'PENDING':
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} is pending deletion")


# ============================================================================
# Global Trigger Endpoints
# ============================================================================

@router.get("", response_model=List[TriggerInstanceResponse])
async def list_all_triggers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List all trigger instances across all agents.

    Returns:
        List of all trigger instances
    """
    try:
        manager = get_trigger_manager()
        triggers = await manager.list_triggers()
        return triggers[offset:offset + limit]
    except Exception as e:
        logger.error(f"Failed to list triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trigger_instance_id}", response_model=TriggerInstanceResponse)
async def get_trigger(trigger_instance_id: str):
    """
    Get a single trigger instance by ID.

    Args:
        trigger_instance_id: UUID of the trigger instance

    Returns:
        Trigger instance details
    """
    try:
        manager = get_trigger_manager()
        trigger = await manager.get_trigger(trigger_instance_id)
        if trigger is None:
            raise HTTPException(status_code=404, detail="Trigger not found")
        return trigger
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trigger {trigger_instance_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Agent-Scoped Trigger Endpoints
# ============================================================================

@agent_triggers_router.get("/{agent_id}/triggers", response_model=List[TriggerInstanceResponse])
async def list_agent_triggers(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    List all triggers for a specific agent.

    Args:
        agent_id: UUID of the agent

    Returns:
        List of trigger instances for the agent
    """
    _check_agent_exists(agent_id, session)

    try:
        manager = get_trigger_manager()
        return await manager.list_agent_triggers(agent_id)
    except Exception as e:
        logger.error(f"Failed to list triggers for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_triggers_router.put("/{agent_id}/triggers", response_model=SetAgentTriggersResponse)
async def set_agent_triggers(
    agent_id: str,
    request: SetAgentTriggersRequest,
    session: Session = Depends(get_session)
):
    """
    Set all triggers for an agent (idempotent).

    This replaces the current set of triggers with the provided list.
    Triggers not in the list are deleted, new ones are created,
    and existing ones are updated if config changed.

    Args:
        agent_id: UUID of the agent
        request: List of trigger configurations

    Returns:
        Final trigger state with counts of created/updated/deleted
    """
    _check_agent_exists(agent_id, session)

    try:
        manager = get_trigger_manager()
        result = await manager.set_agent_triggers(agent_id, request.triggers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set triggers for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_triggers_router.delete("/{agent_id}/triggers", response_model=DeleteAgentTriggersResponse)
async def delete_agent_triggers(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete all triggers for an agent.

    Args:
        agent_id: UUID of the agent

    Returns:
        Deletion confirmation with count
    """
    _check_agent_exists(agent_id, session)

    try:
        manager = get_trigger_manager()
        result = await manager.delete_agent_triggers(agent_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete triggers for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_triggers_router.post("/{agent_id}/triggers/enable", response_model=SetAgentTriggersEnabledResponse)
async def enable_agent_triggers(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Enable all triggers for an agent.

    This also unfreezes FAILED triggers.

    Args:
        agent_id: UUID of the agent

    Returns:
        Confirmation with count of affected triggers
    """
    _check_agent_exists(agent_id, session)

    try:
        manager = get_trigger_manager()
        result = await manager.set_agent_triggers_enabled(agent_id, enabled=True)
        return result
    except Exception as e:
        logger.error(f"Failed to enable triggers for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_triggers_router.post("/{agent_id}/triggers/disable", response_model=SetAgentTriggersEnabledResponse)
async def disable_agent_triggers(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """
    Disable all triggers for an agent.

    Args:
        agent_id: UUID of the agent

    Returns:
        Confirmation with count of affected triggers
    """
    _check_agent_exists(agent_id, session)

    try:
        manager = get_trigger_manager()
        result = await manager.set_agent_triggers_enabled(agent_id, enabled=False)
        return result
    except Exception as e:
        logger.error(f"Failed to disable triggers for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
