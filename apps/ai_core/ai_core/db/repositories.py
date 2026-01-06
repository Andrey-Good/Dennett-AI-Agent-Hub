# apps/ai_core/ai_core/db/repositories.py
"""
Data Access Objects (DAOs) / Repositories for database operations.

This module provides high-level CRUD operations for all domain models,
encapsulating database access and business logic.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import json
import logging

from apps.ai_core.ai_core.db.orm_models import Agent, AgentRun, AgentTestCase, AgentDraft

logger = logging.getLogger(__name__)


class AgentRepository:
    """Data access layer for Agent entities."""

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy Session instance
        """
        self.session = session

    def create(self, name: str, description: Optional[str] = None,
               tags: Optional[List[str]] = None, agent_id: Optional[str] = None,
               version: int = 1, is_active: int = 0,
               deletion_status: str = 'NONE', file_path: Optional[str] = None) -> Agent:
        """
        Create a new agent (v5.0 with versioning support).

        Args:
            name: Agent display name
            description: Agent description
            tags: List of tags for categorization
            agent_id: Optional pre-generated UUIDv7 (for controlled ID generation)
            version: Initial version number (default: 1)
            is_active: Whether triggers are active (default: 0)
            deletion_status: Deletion status (default: 'NONE')
            file_path: Relative path to agent JSON file

        Returns:
            Created Agent instance

        Raises:
            ValueError: If name is empty
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")

        agent = Agent(
            name=name,
            description=description,
            version=version,
            is_active=is_active,
            deletion_status=deletion_status,
            file_path=file_path
        )

        # Set custom ID if provided
        if agent_id:
            agent.id = agent_id

        if tags:
            agent.set_tags(tags)

        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)

        logger.info(f"Created agent: {agent.id} ({agent.name}) v{agent.version}")
        return agent

    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Retrieve agent by ID.
        
        Args:
            agent_id: UUID of the agent
            
        Returns:
            Agent instance or None if not found
        """
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        return agent

    def get_by_name(self, name: str) -> Optional[Agent]:
        """
        Retrieve agent by name.
        
        Args:
            name: Agent name to search for
            
        Returns:
            Agent instance or None if not found
        """
        agent = self.session.query(Agent).filter(Agent.name == name).first()
        return agent

    def list_all(self, limit: int = 100, offset: int = 0,
                  include_pending_deletion: bool = False) -> List[Agent]:
        """
        List all agents with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            include_pending_deletion: If False, exclude agents marked for deletion

        Returns:
            List of Agent instances
        """
        query = self.session.query(Agent)

        # By default, exclude agents pending deletion (v5.0 soft delete)
        if not include_pending_deletion:
            query = query.filter(Agent.deletion_status == 'NONE')

        agents = query \
            .order_by(desc(Agent.modified_at)) \
            .limit(limit) \
            .offset(offset) \
            .all()

        return agents

    def list_by_tags(self, tags: List[str], limit: int = 100) -> List[Agent]:
        """
        Find agents by tags.
        
        Args:
            tags: List of tags to search for (OR logic)
            limit: Maximum number of results
            
        Returns:
            List of matching Agent instances
        """
        agents = self.session.query(Agent).limit(limit).all()
        matching = []

        for agent in agents:
            agent_tags = agent.get_tags()
            if any(tag in agent_tags for tag in tags):
                matching.append(agent)

        return matching

    def update(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """
        Update agent properties.
        
        Args:
            agent_id: UUID of the agent
            **kwargs: Fields to update (name, description, tags)
            
        Returns:
            Updated Agent instance or None if not found
        """
        agent = self.get_by_id(agent_id)
        if not agent:
            return None

        # Handle tags specially
        if 'tags' in kwargs:
            agent.set_tags(kwargs.pop('tags'))

        # Update other fields
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        agent.modified_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(agent)

        logger.info(f"Updated agent: {agent_id}")
        return agent

    def delete(self, agent_id: str) -> bool:
        """
        Delete an agent and all associated data.
        
        Args:
            agent_id: UUID of the agent to delete
            
        Returns:
            True if deleted, False if not found
        """
        agent = self.get_by_id(agent_id)
        if not agent:
            return False

        self.session.delete(agent)
        self.session.commit()

        logger.info(f"Deleted agent: {agent_id}")
        return True

    def count_all(self, include_pending_deletion: bool = False) -> int:
        """
        Count total number of agents.

        Args:
            include_pending_deletion: If False, exclude agents pending deletion

        Returns:
            Number of agents in database
        """
        query = self.session.query(Agent)
        if not include_pending_deletion:
            query = query.filter(Agent.deletion_status == 'NONE')
        return query.count()

    # =========================================================================
    # v5.0 Versioning & Soft Delete Methods
    # =========================================================================

    def mark_for_deletion(self, agent_id: str) -> Optional[Agent]:
        """
        Mark an agent for deletion (soft delete).

        Sets deletion_status to 'PENDING' and is_active to 0.
        Physical deletion is performed by the GarbageCollector worker.

        Args:
            agent_id: UUID of the agent

        Returns:
            Updated Agent instance or None if not found
        """
        agent = self.get_by_id(agent_id)
        if not agent:
            return None

        agent.deletion_status = 'PENDING'
        agent.is_active = 0
        agent.modified_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(agent)

        logger.info(f"Marked agent for deletion: {agent_id}")
        return agent

    def activate(self, agent_id: str) -> Optional[Agent]:
        """
        Activate an agent (set is_active to 1).

        Args:
            agent_id: UUID of the agent

        Returns:
            Updated Agent instance or None if not found/pending deletion
        """
        agent = self.get_by_id(agent_id)
        if not agent or agent.deletion_status == 'PENDING':
            return None

        agent.is_active = 1
        agent.modified_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(agent)

        logger.info(f"Activated agent: {agent_id}")
        return agent

    def deactivate(self, agent_id: str) -> Optional[Agent]:
        """
        Deactivate an agent (set is_active to 0).

        Args:
            agent_id: UUID of the agent

        Returns:
            Updated Agent instance or None if not found/pending deletion
        """
        agent = self.get_by_id(agent_id)
        if not agent or agent.deletion_status == 'PENDING':
            return None

        agent.is_active = 0
        agent.modified_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(agent)

        logger.info(f"Deactivated agent: {agent_id}")
        return agent

    def update_version(self, agent_id: str, new_version: int,
                       new_file_path: str) -> Optional[Agent]:
        """
        Update agent version and file path after deployment.

        Args:
            agent_id: UUID of the agent
            new_version: New version number
            new_file_path: Path to new version file

        Returns:
            Updated Agent instance or None if not found
        """
        agent = self.get_by_id(agent_id)
        if not agent or agent.deletion_status == 'PENDING':
            return None

        agent.version = new_version
        agent.file_path = new_file_path
        agent.modified_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(agent)

        logger.info(f"Updated agent version: {agent_id} -> v{new_version}")
        return agent

    def list_pending_deletion(self) -> List[Agent]:
        """
        List all agents marked for deletion.

        Returns:
            List of Agent instances with deletion_status='PENDING'
        """
        return self.session.query(Agent) \
            .filter(Agent.deletion_status == 'PENDING') \
            .all()

    def hard_delete(self, agent_id: str) -> bool:
        """
        Permanently delete an agent (used by GarbageCollector).

        Args:
            agent_id: UUID of the agent

        Returns:
            True if deleted, False if not found
        """
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return False

        self.session.delete(agent)
        self.session.commit()

        logger.info(f"Hard deleted agent: {agent_id}")
        return True


class AgentRunRepository:
    """Data access layer for AgentRun entities."""

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy Session instance
        """
        self.session = session

    def create(self, agent_id: str, trigger_type: str,
               status: str = "pending", priority: int = 30) -> AgentRun:
        """
        Create a new agent run.
        
        Args:
            agent_id: UUID of the agent
            trigger_type: How the run was triggered
            status: Initial status (default: "pending")
            priority: Task priority (default: 30)
            
        Returns:
            Created AgentRun instance
            
        Raises:
            ValueError: If agent doesn't exist
        """
        # Verify agent exists
        if not self.session.query(Agent).filter(Agent.id == agent_id).first():
            raise ValueError(f"Agent {agent_id} not found")

        run = AgentRun(
            agent_id=agent_id,
            status=status,
            trigger_type=trigger_type,
            priority=priority,
            start_time=datetime.utcnow()
        )

        self.session.add(run)
        self.session.commit()

        logger.info(f"Created agent run: {run.run_id} for agent {agent_id}")
        return run

    def get_by_id(self, run_id: str) -> Optional[AgentRun]:
        """
        Retrieve run by ID.
        
        Args:
            run_id: UUID of the run
            
        Returns:
            AgentRun instance or None if not found
        """
        return self.session.query(AgentRun).filter(AgentRun.run_id == run_id).first()

    def list_by_agent(self, agent_id: str, limit: int = 50,
                      offset: int = 0) -> List[AgentRun]:
        """
        List all runs for a specific agent.
        
        Args:
            agent_id: UUID of the agent
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of AgentRun instances
        """
        return self.session.query(AgentRun) \
            .filter(AgentRun.agent_id == agent_id) \
            .order_by(desc(AgentRun.start_time)) \
            .limit(limit) \
            .offset(offset) \
            .all()

    def list_recent(self, hours: int = 24, limit: int = 100) -> List[AgentRun]:
        """
        List recent runs from the last N hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of results
            
        Returns:
            List of recent AgentRun instances
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(AgentRun) \
            .filter(AgentRun.start_time >= since) \
            .order_by(desc(AgentRun.start_time)) \
            .limit(limit) \
            .all()

    def update_status(self, run_id: str, status: str,
                      error_message: Optional[str] = None) -> Optional[AgentRun]:
        """
        Update run status and optionally error message.
        
        Args:
            run_id: UUID of the run
            status: New status
            error_message: Error details if status is "failed"
            
        Returns:
            Updated AgentRun instance or None if not found
        """
        run = self.get_by_id(run_id)
        if not run:
            return None

        run.status = status
        if error_message:
            run.error_message = error_message

        if status != "running" and status != "pending":
            run.end_time = datetime.utcnow()

        self.session.commit()

        logger.info(f"Updated run {run_id} status to {status}")
        return run

    def get_statistics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get run statistics for an agent.
        
        Args:
            agent_id: UUID of the agent
            
        Returns:
            Dictionary with statistics (total, completed, failed, avg_duration, etc.)
        """
        runs = self.session.query(AgentRun) \
            .filter(AgentRun.agent_id == agent_id) \
            .all()

        if not runs:
            return {
                "total_runs": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "avg_duration_seconds": None
            }

        completed = [r for r in runs if r.is_completed()]
        failed = [r for r in runs if r.has_error()]

        durations = [r.get_duration_seconds() for r in completed
                     if r.get_duration_seconds() is not None]

        return {
            "total_runs": len(runs),
            "completed": len(completed),
            "failed": len(failed),
            "pending": len([r for r in runs if r.status == "pending"]),
            "success_rate": len(completed) / len(runs) if runs else 0,
            "avg_duration_seconds": sum(durations) / len(durations) if durations else None
        }

    def delete_old_runs(self, days: int = 30) -> int:
        """
        Delete runs older than N days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted runs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = self.session.query(AgentRun) \
            .filter(AgentRun.start_time < cutoff_date) \
            .delete()

        self.session.commit()

        logger.info(f"Deleted {deleted} old runs (older than {days} days)")
        return deleted


class AgentTestCaseRepository:
    """Data access layer for AgentTestCase entities."""

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy Session instance
        """
        self.session = session

    def create(self, agent_id: str, node_id: str, name: str,
               initial_state: Dict[str, Any]) -> AgentTestCase:
        """
        Create a new test case.
        
        Args:
            agent_id: UUID of the agent
            node_id: Node ID for state insertion point
            name: Test case name
            initial_state: Initial state dictionary
            
        Returns:
            Created AgentTestCase instance
            
        Raises:
            ValueError: If agent doesn't exist
        """
        # Verify agent exists
        if not self.session.query(Agent).filter(Agent.id == agent_id).first():
            raise ValueError(f"Agent {agent_id} not found")

        existing = self.session.query(AgentTestCase) \
            .filter(and_(
            AgentTestCase.agent_id == agent_id,
            AgentTestCase.node_id == node_id,
            AgentTestCase.name == name
        )) \
            .first()

        if existing:
            raise ValueError(
                f"Test case with name '{name}' already exists for agent {agent_id} "
                f"and node {node_id}"
            )

        test_case = AgentTestCase(
            agent_id=agent_id,
            node_id=node_id,
            name=name
        )
        test_case.set_initial_state(initial_state)

        self.session.add(test_case)

        try:
            self.session.commit()
            self.session.refresh(test_case)
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Test case with name '{name}' already exists for agent {agent_id} "
                f"and node {node_id}"
            ) from e

        logger.info(f"Created test case: {test_case.case_id} for agent {agent_id}")
        return test_case

    def get_by_id(self, case_id: str) -> Optional[AgentTestCase]:
        """
        Retrieve test case by ID.
        
        Args:
            case_id: UUID of the test case
            
        Returns:
            AgentTestCase instance or None if not found
        """
        test_case = self.session.query(AgentTestCase) \
            .filter(AgentTestCase.case_id == case_id) \
            .first()

        return test_case

    def list_by_agent(self, agent_id: str) -> List[AgentTestCase]:
        """
        List all test cases for an agent.
        
        Args:
            agent_id: UUID of the agent
            
        Returns:
            List of AgentTestCase instances
        """
        test_cases = self.session.query(AgentTestCase) \
            .filter(AgentTestCase.agent_id == agent_id) \
            .all()

        return test_cases

    def list_by_node(self, agent_id: str, node_id: str) -> List[AgentTestCase]:
        """
        List test cases for a specific node.
        
        Args:
            agent_id: UUID of the agent
            node_id: Node ID to filter by
            
        Returns:
            List of matching AgentTestCase instances
        """
        test_cases = self.session.query(AgentTestCase) \
            .filter(and_(
            AgentTestCase.agent_id == agent_id,
            AgentTestCase.node_id == node_id
        )) \
            .all()

        return test_cases

    def update(self, case_id: str, **kwargs) -> Optional[AgentTestCase]:
        """
        Update test case properties.
        
        Args:
            case_id: UUID of the test case
            **kwargs: Fields to update (name, initial_state)
            
        Returns:
            Updated AgentTestCase instance or None if not found
        """
        test_case = self.get_by_id(case_id)
        if not test_case:
            return None

        # Handle initial_state specially
        if 'initial_state' in kwargs:
            test_case.set_initial_state(kwargs.pop('initial_state'))

        # Update other fields
        for key, value in kwargs.items():
            if hasattr(test_case, key):
                setattr(test_case, key, value)

        self.session.commit()
        self.session.refresh(test_case)

        logger.info(f"Updated test case: {case_id}")
        return test_case

    def delete(self, case_id: str) -> bool:
        """
        Delete a test case.
        
        Args:
            case_id: UUID of the test case
            
        Returns:
            True if deleted, False if not found
        """
        test_case = self.get_by_id(case_id)
        if not test_case:
            return False

        self.session.delete(test_case)
        self.session.commit()

        logger.info(f"Deleted test case: {case_id}")
        return True

    def count_by_agent(self, agent_id: str) -> int:
        """
        Count test cases for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            Number of test cases
        """
        return self.session.query(AgentTestCase) \
            .filter(AgentTestCase.agent_id == agent_id) \
            .count()


class AgentDraftRepository:
    """
    Data access layer for AgentDraft entities (v5.0).

    Manages draft/branch versions of agents for development and testing.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy Session instance
        """
        self.session = session

    def create(self, agent_id: str, name: str, file_path: str,
               base_version: int, draft_id: Optional[str] = None) -> AgentDraft:
        """
        Create a new draft for an agent.

        Args:
            agent_id: UUID of the parent agent
            name: Draft/branch name
            file_path: Relative path to draft JSON file
            base_version: Version this draft is based on
            draft_id: Optional pre-generated draft ID

        Returns:
            Created AgentDraft instance

        Raises:
            ValueError: If agent doesn't exist
        """
        # Verify agent exists and is not pending deletion
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        if agent.deletion_status == 'PENDING':
            raise ValueError(f"Agent {agent_id} is pending deletion")

        # Generate ISO timestamp with milliseconds
        updated_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        draft = AgentDraft(
            agent_id=agent_id,
            name=name,
            file_path=file_path,
            base_version=base_version,
            updated_at=updated_at
        )

        if draft_id:
            draft.draft_id = draft_id

        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)

        logger.info(f"Created draft: {draft.draft_id} for agent {agent_id}")
        return draft

    def get_by_id(self, draft_id: str) -> Optional[AgentDraft]:
        """
        Retrieve draft by ID.

        Args:
            draft_id: UUID of the draft

        Returns:
            AgentDraft instance or None if not found
        """
        return self.session.query(AgentDraft) \
            .filter(AgentDraft.draft_id == draft_id) \
            .first()

    def get_by_id_and_agent(self, draft_id: str, agent_id: str) -> Optional[AgentDraft]:
        """
        Retrieve draft by ID, verifying it belongs to the specified agent.

        Args:
            draft_id: UUID of the draft
            agent_id: UUID of the agent

        Returns:
            AgentDraft instance or None if not found or wrong agent
        """
        return self.session.query(AgentDraft) \
            .filter(and_(
                AgentDraft.draft_id == draft_id,
                AgentDraft.agent_id == agent_id
            )) \
            .first()

    def list_by_agent(self, agent_id: str) -> List[AgentDraft]:
        """
        List all drafts for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            List of AgentDraft instances ordered by updated_at DESC
        """
        return self.session.query(AgentDraft) \
            .filter(AgentDraft.agent_id == agent_id) \
            .order_by(desc(AgentDraft.updated_at)) \
            .all()

    def update(self, draft_id: str, name: Optional[str] = None,
               touch_updated_at: bool = True) -> Optional[AgentDraft]:
        """
        Update draft metadata.

        Args:
            draft_id: UUID of the draft
            name: New name (optional)
            touch_updated_at: Whether to update the updated_at timestamp

        Returns:
            Updated AgentDraft instance or None if not found
        """
        draft = self.get_by_id(draft_id)
        if not draft:
            return None

        if name is not None:
            draft.name = name

        if touch_updated_at:
            draft.updated_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        self.session.commit()
        self.session.refresh(draft)

        logger.info(f"Updated draft: {draft_id}")
        return draft

    def update_with_lock_check(self, draft_id: str, agent_id: str,
                               expected_updated_at: Optional[str] = None,
                               name: Optional[str] = None) -> Optional[AgentDraft]:
        """
        Update draft with optional optimistic locking.

        Args:
            draft_id: UUID of the draft
            agent_id: UUID of the agent (for verification)
            expected_updated_at: Expected timestamp for optimistic locking
            name: New name (optional)

        Returns:
            Updated AgentDraft instance

        Raises:
            ValueError: If optimistic lock fails (concurrent modification)
        """
        draft = self.get_by_id_and_agent(draft_id, agent_id)
        if not draft:
            return None

        # Optimistic locking check
        if expected_updated_at and draft.updated_at != expected_updated_at:
            raise ValueError("Conflict: draft was modified by another process")

        if name is not None:
            draft.name = name

        draft.updated_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        self.session.commit()
        self.session.refresh(draft)

        return draft

    def delete(self, draft_id: str) -> bool:
        """
        Delete a draft.

        Args:
            draft_id: UUID of the draft

        Returns:
            True if deleted, False if not found
        """
        draft = self.get_by_id(draft_id)
        if not draft:
            return False

        self.session.delete(draft)
        self.session.commit()

        logger.info(f"Deleted draft: {draft_id}")
        return True

    def delete_by_agent(self, agent_id: str) -> int:
        """
        Delete all drafts for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            Number of drafts deleted
        """
        count = self.session.query(AgentDraft) \
            .filter(AgentDraft.agent_id == agent_id) \
            .delete()

        self.session.commit()

        logger.info(f"Deleted {count} drafts for agent {agent_id}")
        return count

    def count_by_agent(self, agent_id: str) -> int:
        """
        Count drafts for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            Number of drafts
        """
        return self.session.query(AgentDraft) \
            .filter(AgentDraft.agent_id == agent_id) \
            .count()
