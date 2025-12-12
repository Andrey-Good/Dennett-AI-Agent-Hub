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

from apps.ai_core.ai_core.db.orm_models import Agent, AgentRun, AgentTestCase

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
               tags: Optional[List[str]] = None) -> Agent:
        """
        Create a new agent.
        
        Args:
            name: Agent display name
            description: Agent description
            tags: List of tags for categorization
            
        Returns:
            Created Agent instance
            
        Raises:
            ValueError: If name is empty
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")

        agent = Agent(name=name, description=description)
        if tags:
            agent.set_tags(tags)

        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)

        agent.tags = agent.get_tags()

        logger.info(f"Created agent: {agent.id} ({agent.name})")
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
        if agent:
            agent.tags = agent.get_tags()
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
        if agent:
            agent.tags = agent.get_tags()
        return agent

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Agent]:
        """
        List all agents with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Agent instances
        """
        agents = self.session.query(Agent) \
            .order_by(desc(Agent.created_at)) \
            .limit(limit) \
            .offset(offset) \
            .all()

        for agent in agents:
            agent.tags = agent.get_tags()

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

        agent.tags = agent.get_tags()

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

    def count_all(self) -> int:
        """
        Count total number of agents.
        
        Returns:
            Number of agents in database
        """
        return self.session.query(Agent).count()


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

        # Deserialize initial_state for response (check type first)
        if isinstance(test_case.initial_state, str):
            test_case.initial_state = test_case.get_initial_state()

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

        if test_case:
            if isinstance(test_case.initial_state, str):
                test_case.initial_state = test_case.get_initial_state()

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

        for test_case in test_cases:
            if isinstance(test_case.initial_state, str):
                test_case.initial_state = test_case.get_initial_state()

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

        # Deserialize initial_state for all test cases
        for test_case in test_cases:
            if isinstance(test_case.initial_state, str):
                test_case.initial_state = test_case.get_initial_state()

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

        # Deserialize initial_state for response (check type first)
        if isinstance(test_case.initial_state, str):
            test_case.initial_state = test_case.get_initial_state()

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
