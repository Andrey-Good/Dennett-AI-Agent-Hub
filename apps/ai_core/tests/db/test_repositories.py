# apps/ai_core/ai_core/tests/db/test_repositories.py
"""
Unit tests for database repositories using in-memory SQLite.

This test suite covers CRUD operations for Agent, AgentRun, and AgentTestCase
repositories using a temporary in-memory SQLite database.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from apps.ai_core.ai_core.db.orm_models import Base, Agent, AgentRun, AgentTestCase
from apps.ai_core.ai_core.db.repositories import (
    AgentRepository, AgentRunRepository, AgentTestCaseRepository
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield SessionLocal
    
    engine.dispose()


@pytest.fixture
def db_session(in_memory_db):
    """Provide a database session for a single test."""
    session = in_memory_db()
    
    yield session
    
    session.close()


# ============================================================================
# Agent Repository Tests
# ============================================================================

class TestAgentRepository:
    """Test suite for AgentRepository."""
    
    def test_create_agent(self, db_session: Session):
        """Test creating a new agent."""
        repo = AgentRepository(db_session)
        
        agent = repo.create(
            name="Test Agent",
            description="A test agent",
            tags=["test", "sample"]
        )
        
        assert agent.id is not None
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
        assert agent.get_tags() == ["test", "sample"]
        assert agent.created_at is not None
        assert agent.modified_at is not None
    
    def test_create_agent_empty_name_fails(self, db_session: Session):
        """Test that creating agent with empty name raises ValueError."""
        repo = AgentRepository(db_session)
        
        with pytest.raises(ValueError):
            repo.create(name="")
    
    def test_get_agent_by_id(self, db_session: Session):
        """Test retrieving agent by ID."""
        repo = AgentRepository(db_session)
        
        created = repo.create(name="Test Agent")
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Agent"
    
    def test_get_agent_by_id_not_found(self, db_session: Session):
        """Test getting non-existent agent returns None."""
        repo = AgentRepository(db_session)
        
        result = repo.get_by_id("non-existent-id")
        
        assert result is None
    
    def test_get_agent_by_name(self, db_session: Session):
        """Test retrieving agent by name."""
        repo = AgentRepository(db_session)
        
        created = repo.create(name="Named Agent")
        retrieved = repo.get_by_name("Named Agent")
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_list_all_agents(self, db_session: Session):
        """Test listing all agents."""
        repo = AgentRepository(db_session)
        
        agent1 = repo.create(name="Agent 1")
        agent2 = repo.create(name="Agent 2")
        agent3 = repo.create(name="Agent 3")
        
        agents = repo.list_all(limit=10, offset=0)
        
        assert len(agents) == 3
        assert any(a.id == agent1.id for a in agents)
        assert any(a.id == agent2.id for a in agents)
        assert any(a.id == agent3.id for a in agents)
    
    def test_list_agents_with_pagination(self, db_session: Session):
        """Test agent listing with pagination."""
        repo = AgentRepository(db_session)
        
        for i in range(5):
            repo.create(name=f"Agent {i}")
        
        page1 = repo.list_all(limit=2, offset=0)
        page2 = repo.list_all(limit=2, offset=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id
    
    def test_update_agent(self, db_session: Session):
        """Test updating agent properties."""
        repo = AgentRepository(db_session)
        
        agent = repo.create(name="Original Name", tags=["old"])
        
        updated = repo.update(
            agent.id,
            name="Updated Name",
            tags=["new", "updated"]
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.get_tags() == ["new", "updated"]
    
    def test_update_agent_not_found(self, db_session: Session):
        """Test updating non-existent agent returns None."""
        repo = AgentRepository(db_session)
        
        result = repo.update("non-existent-id", name="New Name")
        
        assert result is None
    
    def test_delete_agent(self, db_session: Session):
        """Test deleting an agent."""
        repo = AgentRepository(db_session)
        
        agent = repo.create(name="Agent to Delete")
        
        deleted = repo.delete(agent.id)
        
        assert deleted is True
        assert repo.get_by_id(agent.id) is None
    
    def test_delete_agent_not_found(self, db_session: Session):
        """Test deleting non-existent agent returns False."""
        repo = AgentRepository(db_session)
        
        result = repo.delete("non-existent-id")
        
        assert result is False
    
    def test_count_agents(self, db_session: Session):
        """Test counting agents."""
        repo = AgentRepository(db_session)
        
        assert repo.count_all() == 0
        
        repo.create(name="Agent 1")
        repo.create(name="Agent 2")
        
        assert repo.count_all() == 2


# ============================================================================
# Agent Run Repository Tests
# ============================================================================

class TestAgentRunRepository:
    """Test suite for AgentRunRepository."""

    def test_create_run(self, db_session: Session):
        """Test creating a new agent run."""
        repo = AgentRunRepository(db_session)
        agent_repo = AgentRepository(db_session)
        agent = agent_repo.create(name="Test Agent")
        
        run = repo.create(
            agent_id=agent.id,
            trigger_type="manual",
            status="pending"
        )
        
        assert run.run_id is not None
        assert run.agent_id == agent.id
        assert run.status == "pending"
        assert run.trigger_type == "manual"
        assert run.start_time is not None
    
    def test_create_run_invalid_agent(self, db_session: Session):
        """Test creating run with non-existent agent raises ValueError."""
        repo = AgentRunRepository(db_session)
        
        with pytest.raises(ValueError):
            repo.create(
                agent_id="non-existent-agent",
                trigger_type="manual"
            )
    
    def test_get_run_by_id(self, db_session: Session):
        """Test retrieving run by ID."""
        repo = AgentRunRepository(db_session)
        agent_repo = AgentRepository(db_session)
        agent = agent_repo.create(name="Test Agent")
        
        created = repo.create(agent_id=agent.id, trigger_type="manual")
        retrieved = repo.get_by_id(created.run_id)
        
        assert retrieved is not None
        assert retrieved.run_id == created.run_id
    
    def test_list_runs_by_agent(self, db_session: Session):
        """Test listing runs for a specific agent."""
        repo = AgentRunRepository(db_session)
        agent_repo = AgentRepository(db_session)
        agent = agent_repo.create(name="Test Agent")
        
        run1 = repo.create(agent_id=agent.id, trigger_type="manual")
        run2 = repo.create(agent_id=agent.id, trigger_type="schedule")
        
        runs = repo.list_by_agent(agent.id)
        
        assert len(runs) == 2
        assert any(r.run_id == run1.run_id for r in runs)
        assert any(r.run_id == run2.run_id for r in runs)
    
    def test_update_run_status(self, db_session: Session):
        """Test updating run status."""
        repo = AgentRunRepository(db_session)
        agent_repo = AgentRepository(db_session)
        agent = agent_repo.create(name="Test Agent")
        
        run = repo.create(agent_id=agent.id, trigger_type="manual", status="pending")
        
        updated = repo.update_status(run.run_id, "completed")
        
        assert updated is not None
        assert updated.status == "completed"
        assert updated.end_time is not None
    
    def test_update_run_status_with_error(self, db_session: Session):
        """Test updating run status with error message."""
        repo = AgentRunRepository(db_session)
        agent_repo = AgentRepository(db_session)
        agent = agent_repo.create(name="Test Agent")
        
        run = repo.create(agent_id=agent.id, trigger_type="manual")
        
        error_msg = "Something went wrong"
        updated = repo.update_status(run.run_id, "failed", error_message=error_msg)
        
        assert updated.status == "failed"
        assert updated.error_message == error_msg
    
    def test_get_statistics(self, db_session: Session):
        """Test getting run statistics."""
        repo = AgentRunRepository(db_session)
        agent_repo = AgentRepository(db_session)
        agent = agent_repo.create(name="Test Agent")
        
        # Create runs with different statuses
        run1 = repo.create(agent_id=agent.id, trigger_type="manual")
        repo.update_status(run1.run_id, "completed")
        
        run2 = repo.create(agent_id=agent.id, trigger_type="manual")
        repo.update_status(run2.run_id, "failed", error_message="Error")
        
        stats = repo.get_statistics(agent.id)
        
        assert stats["total_runs"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5


# ============================================================================
# Agent Test Case Repository Tests
# ============================================================================

class TestAgentTestCaseRepository:
    """Test suite for AgentTestCaseRepository."""
    
    def test_create_test_case(self, db_session: Session):
        """Test creating a new test case."""
        agent_repo = AgentRepository(db_session)
        test_repo = AgentTestCaseRepository(db_session)
        
        agent = agent_repo.create(name="Test Agent")
        
        test_case = test_repo.create(
            agent_id=agent.id,
            node_id="node_001",
            name="Test Case 1",
            initial_state={"input": "test", "expected": "output"}
        )
        
        assert test_case.case_id is not None
        assert test_case.agent_id == agent.id
        assert test_case.node_id == "node_001"
        assert test_case.name == "Test Case 1"
        assert test_case.get_initial_state() == {"input": "test", "expected": "output"}
    
    def test_list_test_cases_by_agent(self, db_session: Session):
        """Test listing test cases for an agent."""
        agent_repo = AgentRepository(db_session)
        test_repo = AgentTestCaseRepository(db_session)
        
        agent = agent_repo.create(name="Test Agent")
        
        tc1 = test_repo.create(
            agent_id=agent.id,
            node_id="node_001",
            name="Test 1",
            initial_state={"a": 1}
        )
        tc2 = test_repo.create(
            agent_id=agent.id,
            node_id="node_002",
            name="Test 2",
            initial_state={"b": 2}
        )
        
        test_cases = test_repo.list_by_agent(agent.id)
        
        assert len(test_cases) == 2
        assert any(tc.case_id == tc1.case_id for tc in test_cases)
        assert any(tc.case_id == tc2.case_id for tc in test_cases)
    
    def test_delete_test_case(self, db_session: Session):
        """Test deleting a test case."""
        agent_repo = AgentRepository(db_session)
        test_repo = AgentTestCaseRepository(db_session)
        
        agent = agent_repo.create(name="Test Agent")
        test_case = test_repo.create(
            agent_id=agent.id,
            node_id="node_001",
            name="Test",
            initial_state={}
        )
        
        deleted = test_repo.delete(test_case.case_id)
        
        assert deleted is True
        assert test_repo.get_by_id(test_case.case_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
