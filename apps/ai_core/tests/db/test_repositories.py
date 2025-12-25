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

try:
    from apps.ai_core.ai_core.db.orm_models import Base, Agent, AgentRun, AgentTestCase
    from apps.ai_core.ai_core.db.repositories import (
        AgentRepository, AgentRunRepository, AgentTestCaseRepository, AgentDraftRepository
    )
except ModuleNotFoundError:
    from ai_core.db.orm_models import Base, Agent, AgentRun, AgentTestCase
    from ai_core.db.repositories import (
        AgentRepository, AgentRunRepository, AgentTestCaseRepository, AgentDraftRepository
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
        # Tags are stored as JSON string, use get_tags() to deserialize
        tags = agent.get_tags()
        assert tags == ["test", "sample"]
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
        # Tags are stored as JSON string, use get_tags() to deserialize
        tags = updated.get_tags()
        assert tags == ["new", "updated"]
    
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
        # initial_state is stored as JSON string, use get_initial_state()
        state = test_case.get_initial_state()
        assert state == {"input": "test", "expected": "output"}
    
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


# ============================================================================
# Agent Repository v5.0 Tests (Soft Delete, Versioning)
# ============================================================================

class TestAgentRepositoryV5:
    """Test suite for v5.0 Agent features: soft delete, versioning."""

    def test_create_agent_with_v5_fields(self, db_session: Session):
        """Test creating agent with v5.0 fields."""
        repo = AgentRepository(db_session)

        agent = repo.create(
            name="V5 Agent",
            description="Agent with versioning",
            version=1,
            is_active=0,
            deletion_status='NONE',
            file_path="agent-123/v1.json"
        )

        assert agent.version == 1
        assert agent.is_active == 0
        assert agent.deletion_status == 'NONE'
        assert agent.file_path == "agent-123/v1.json"

    def test_mark_for_deletion(self, db_session: Session):
        """Test soft delete (mark for deletion)."""
        repo = AgentRepository(db_session)
        agent = repo.create(name="To Delete", is_active=1)

        result = repo.mark_for_deletion(agent.id)

        assert result is not None
        assert result.deletion_status == 'PENDING'
        assert result.is_active == 0

    def test_mark_for_deletion_nonexistent_agent(self, db_session: Session):
        """Test marking non-existent agent for deletion returns None."""
        repo = AgentRepository(db_session)

        result = repo.mark_for_deletion("nonexistent-id")

        assert result is None

    def test_list_all_excludes_pending_deletion(self, db_session: Session):
        """Test that list_all excludes agents pending deletion by default."""
        repo = AgentRepository(db_session)

        agent1 = repo.create(name="Active Agent")
        agent2 = repo.create(name="Deleted Agent")
        repo.mark_for_deletion(agent2.id)

        agents = repo.list_all()

        assert len(agents) == 1
        assert agents[0].id == agent1.id

    def test_list_all_includes_pending_deletion(self, db_session: Session):
        """Test that list_all can include pending deletion agents."""
        repo = AgentRepository(db_session)

        agent1 = repo.create(name="Active Agent")
        agent2 = repo.create(name="Deleted Agent")
        repo.mark_for_deletion(agent2.id)

        agents = repo.list_all(include_pending_deletion=True)

        assert len(agents) == 2

    def test_activate_agent(self, db_session: Session):
        """Test activating an agent."""
        repo = AgentRepository(db_session)
        agent = repo.create(name="Inactive Agent", is_active=0)

        result = repo.activate(agent.id)

        assert result is not None
        assert result.is_active == 1

    def test_activate_pending_deletion_fails(self, db_session: Session):
        """Test that activating pending deletion agent fails."""
        repo = AgentRepository(db_session)
        agent = repo.create(name="Deleted Agent")
        repo.mark_for_deletion(agent.id)

        result = repo.activate(agent.id)

        assert result is None

    def test_deactivate_agent(self, db_session: Session):
        """Test deactivating an agent."""
        repo = AgentRepository(db_session)
        agent = repo.create(name="Active Agent", is_active=1)

        result = repo.deactivate(agent.id)

        assert result is not None
        assert result.is_active == 0

    def test_update_version(self, db_session: Session):
        """Test updating agent version and file path."""
        repo = AgentRepository(db_session)
        agent = repo.create(
            name="Versioned Agent",
            version=1,
            file_path="agent-1/v1.json"
        )

        result = repo.update_version(agent.id, 2, "agent-1/v2.json")

        assert result is not None
        assert result.version == 2
        assert result.file_path == "agent-1/v2.json"

    def test_list_pending_deletion(self, db_session: Session):
        """Test listing agents pending deletion."""
        repo = AgentRepository(db_session)

        agent1 = repo.create(name="Active 1")
        agent2 = repo.create(name="Pending 1")
        agent3 = repo.create(name="Active 2")
        agent4 = repo.create(name="Pending 2")

        repo.mark_for_deletion(agent2.id)
        repo.mark_for_deletion(agent4.id)

        pending = repo.list_pending_deletion()

        assert len(pending) == 2
        pending_ids = [a.id for a in pending]
        assert agent2.id in pending_ids
        assert agent4.id in pending_ids

    def test_hard_delete(self, db_session: Session):
        """Test permanent deletion of agent."""
        repo = AgentRepository(db_session)
        agent = repo.create(name="To Hard Delete")

        result = repo.hard_delete(agent.id)

        assert result is True
        assert repo.get_by_id(agent.id) is None

    def test_hard_delete_nonexistent(self, db_session: Session):
        """Test hard delete of non-existent agent returns False."""
        repo = AgentRepository(db_session)

        result = repo.hard_delete("nonexistent-id")

        assert result is False

    def test_count_excludes_pending_deletion(self, db_session: Session):
        """Test count excludes pending deletion by default."""
        repo = AgentRepository(db_session)

        repo.create(name="Agent 1")
        agent2 = repo.create(name="Agent 2")
        repo.create(name="Agent 3")
        repo.mark_for_deletion(agent2.id)

        count = repo.count_all()

        assert count == 2


# ============================================================================
# Agent Draft Repository Tests
# ============================================================================

class TestAgentDraftRepository:
    """Test suite for AgentDraftRepository."""

    def test_create_draft(self, db_session: Session):
        """Test creating a new draft."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent", version=1)

        draft = draft_repo.create(
            agent_id=agent.id,
            name="Experiment Draft",
            file_path=f"{agent.id}/drafts/draft-1.json",
            base_version=1
        )

        assert draft.draft_id is not None
        assert draft.agent_id == agent.id
        assert draft.name == "Experiment Draft"
        assert draft.base_version == 1
        assert draft.updated_at is not None

    def test_create_draft_with_custom_id(self, db_session: Session):
        """Test creating a draft with pre-generated ID."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        custom_id = "custom-draft-id-123"

        draft = draft_repo.create(
            agent_id=agent.id,
            name="Custom ID Draft",
            file_path=f"{agent.id}/drafts/{custom_id}.json",
            base_version=1,
            draft_id=custom_id
        )

        assert draft.draft_id == custom_id

    def test_create_draft_for_nonexistent_agent_fails(self, db_session: Session):
        """Test creating draft for non-existent agent raises ValueError."""
        draft_repo = AgentDraftRepository(db_session)

        with pytest.raises(ValueError) as exc_info:
            draft_repo.create(
                agent_id="nonexistent-agent",
                name="Draft",
                file_path="path.json",
                base_version=1
            )

        assert "not found" in str(exc_info.value)

    def test_create_draft_for_pending_deletion_fails(self, db_session: Session):
        """Test creating draft for pending deletion agent fails."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Deleted Agent")
        agent_repo.mark_for_deletion(agent.id)

        with pytest.raises(ValueError) as exc_info:
            draft_repo.create(
                agent_id=agent.id,
                name="Draft",
                file_path="path.json",
                base_version=1
            )

        assert "pending deletion" in str(exc_info.value)

    def test_get_draft_by_id(self, db_session: Session):
        """Test retrieving draft by ID."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        created = draft_repo.create(
            agent_id=agent.id,
            name="Draft",
            file_path="path.json",
            base_version=1
        )

        retrieved = draft_repo.get_by_id(created.draft_id)

        assert retrieved is not None
        assert retrieved.draft_id == created.draft_id
        assert retrieved.name == "Draft"

    def test_get_draft_by_id_and_agent(self, db_session: Session):
        """Test retrieving draft by ID with agent verification."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent1 = agent_repo.create(name="Agent 1")
        agent2 = agent_repo.create(name="Agent 2")

        draft = draft_repo.create(
            agent_id=agent1.id,
            name="Draft",
            file_path="path.json",
            base_version=1
        )

        # Should find draft with correct agent
        result1 = draft_repo.get_by_id_and_agent(draft.draft_id, agent1.id)
        assert result1 is not None

        # Should not find draft with wrong agent
        result2 = draft_repo.get_by_id_and_agent(draft.draft_id, agent2.id)
        assert result2 is None

    def test_list_drafts_by_agent(self, db_session: Session):
        """Test listing all drafts for an agent."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")

        draft1 = draft_repo.create(
            agent_id=agent.id,
            name="Draft 1",
            file_path="d1.json",
            base_version=1
        )
        draft2 = draft_repo.create(
            agent_id=agent.id,
            name="Draft 2",
            file_path="d2.json",
            base_version=1
        )

        drafts = draft_repo.list_by_agent(agent.id)

        assert len(drafts) == 2
        draft_ids = [d.draft_id for d in drafts]
        assert draft1.draft_id in draft_ids
        assert draft2.draft_id in draft_ids

    def test_list_drafts_ordered_by_updated_at(self, db_session: Session):
        """Test that drafts are ordered by updated_at DESC."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")

        # Create drafts in order
        draft1 = draft_repo.create(
            agent_id=agent.id,
            name="First",
            file_path="d1.json",
            base_version=1
        )
        draft2 = draft_repo.create(
            agent_id=agent.id,
            name="Second",
            file_path="d2.json",
            base_version=1
        )

        # Update first draft to make it newer
        draft_repo.update(draft1.draft_id, touch_updated_at=True)

        drafts = draft_repo.list_by_agent(agent.id)

        # First draft should now be first (most recent)
        assert drafts[0].draft_id == draft1.draft_id

    def test_update_draft_name(self, db_session: Session):
        """Test updating draft name."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        draft = draft_repo.create(
            agent_id=agent.id,
            name="Original Name",
            file_path="path.json",
            base_version=1
        )

        updated = draft_repo.update(draft.draft_id, name="New Name")

        assert updated is not None
        assert updated.name == "New Name"

    def test_update_with_lock_check_success(self, db_session: Session):
        """Test update with optimistic locking - success case."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        draft = draft_repo.create(
            agent_id=agent.id,
            name="Draft",
            file_path="path.json",
            base_version=1
        )
        original_updated_at = draft.updated_at

        updated = draft_repo.update_with_lock_check(
            draft_id=draft.draft_id,
            agent_id=agent.id,
            expected_updated_at=original_updated_at,
            name="Updated Name"
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.updated_at != original_updated_at

    def test_update_with_lock_check_conflict(self, db_session: Session):
        """Test update with optimistic locking - conflict case."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        draft = draft_repo.create(
            agent_id=agent.id,
            name="Draft",
            file_path="path.json",
            base_version=1
        )

        # Simulate concurrent modification
        draft_repo.update(draft.draft_id, touch_updated_at=True)

        # Try to update with old timestamp
        with pytest.raises(ValueError) as exc_info:
            draft_repo.update_with_lock_check(
                draft_id=draft.draft_id,
                agent_id=agent.id,
                expected_updated_at="old-timestamp",
                name="Should Fail"
            )

        assert "Conflict" in str(exc_info.value)

    def test_delete_draft(self, db_session: Session):
        """Test deleting a draft."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        draft = draft_repo.create(
            agent_id=agent.id,
            name="To Delete",
            file_path="path.json",
            base_version=1
        )

        result = draft_repo.delete(draft.draft_id)

        assert result is True
        assert draft_repo.get_by_id(draft.draft_id) is None

    def test_delete_draft_not_found(self, db_session: Session):
        """Test deleting non-existent draft returns False."""
        draft_repo = AgentDraftRepository(db_session)

        result = draft_repo.delete("nonexistent-draft")

        assert result is False

    def test_delete_all_drafts_by_agent(self, db_session: Session):
        """Test deleting all drafts for an agent."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")
        draft_repo.create(agent_id=agent.id, name="D1", file_path="1.json", base_version=1)
        draft_repo.create(agent_id=agent.id, name="D2", file_path="2.json", base_version=1)
        draft_repo.create(agent_id=agent.id, name="D3", file_path="3.json", base_version=1)

        count = draft_repo.delete_by_agent(agent.id)

        assert count == 3
        assert len(draft_repo.list_by_agent(agent.id)) == 0

    def test_count_drafts_by_agent(self, db_session: Session):
        """Test counting drafts for an agent."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        agent = agent_repo.create(name="Test Agent")

        assert draft_repo.count_by_agent(agent.id) == 0

        draft_repo.create(agent_id=agent.id, name="D1", file_path="1.json", base_version=1)
        draft_repo.create(agent_id=agent.id, name="D2", file_path="2.json", base_version=1)

        assert draft_repo.count_by_agent(agent.id) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
