# apps/ai_core/tests/workers/test_garbage_collector.py
"""
Unit tests for AgentGarbageCollector worker.

Tests the background worker that cleans up agents marked for deletion.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

try:
    from apps.ai_core.ai_core.db.orm_models import Base, Agent
    from apps.ai_core.ai_core.db.repositories import AgentRepository, AgentDraftRepository
    from apps.ai_core.ai_core.workers.garbage_collector import (
        AgentGarbageCollector,
        get_garbage_collector,
        init_garbage_collector
    )
except ModuleNotFoundError:
    from ai_core.db.orm_models import Base, Agent
    from ai_core.db.repositories import AgentRepository, AgentDraftRepository
    from ai_core.workers.garbage_collector import (
        AgentGarbageCollector,
        get_garbage_collector,
        init_garbage_collector
    )


class TestAgentGarbageCollectorInit:
    """Test GarbageCollector initialization and singleton."""

    def test_init_with_default_interval(self):
        """Test creating GC with default interval."""
        gc = AgentGarbageCollector()
        assert gc.interval == 300  # 5 minutes default

    def test_init_with_custom_interval(self):
        """Test creating GC with custom interval."""
        gc = AgentGarbageCollector(interval_seconds=60)
        assert gc.interval == 60

    def test_get_garbage_collector(self):
        """Test getting global GC instance."""
        gc = get_garbage_collector()
        assert isinstance(gc, AgentGarbageCollector)

    def test_init_garbage_collector(self):
        """Test initializing global GC with custom interval."""
        gc = init_garbage_collector(interval_seconds=120)
        assert gc.interval == 120

        # get_garbage_collector should return the same instance
        gc2 = get_garbage_collector()
        assert gc2.interval == 120


@pytest.mark.skip(reason="Async worker tests require additional setup for database fixtures")
class TestAgentGarbageCollectorCleanup:
    """Test GarbageCollector cleanup functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for agent files."""
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    @pytest.fixture
    def in_memory_db(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        yield SessionLocal
        engine.dispose()

    @pytest.fixture
    def db_session(self, in_memory_db):
        """Provide a database session for a single test."""
        session = in_memory_db()
        yield session
        session.close()

    @pytest.fixture
    def session_factory(self, in_memory_db):
        """Provide a session factory for GC."""
        return in_memory_db

    def test_stop_method(self):
        """Test that stop() sets _running to False."""
        gc = AgentGarbageCollector()
        gc._running = True

        gc.stop()

        assert gc._running is False

    @pytest.mark.asyncio
    async def test_cleanup_no_pending_agents(self, session_factory, temp_dir, db_session):
        """Test cleanup when no agents are pending deletion."""
        # Create some normal agents (not pending deletion)
        repo = AgentRepository(db_session)
        repo.create(name="Active Agent 1")
        repo.create(name="Active Agent 2")

        gc = AgentGarbageCollector()

        # Run cleanup (should do nothing)
        await gc._cleanup_pending_agents(session_factory, temp_dir)

        # Verify agents still exist
        assert len(repo.list_all()) == 2

    @pytest.mark.asyncio
    async def test_cleanup_pending_agents(self, session_factory, temp_dir, db_session):
        """Test cleanup of agents pending deletion."""
        repo = AgentRepository(db_session)

        # Create agents
        agent1 = repo.create(name="Active Agent")
        agent2 = repo.create(name="To Delete")

        # Create directory for agent2
        agent2_dir = os.path.join(temp_dir, agent2.id)
        os.makedirs(agent2_dir)
        with open(os.path.join(agent2_dir, "v1.json"), 'w') as f:
            f.write('{"test": true}')

        # Mark agent2 for deletion
        repo.mark_for_deletion(agent2.id)

        gc = AgentGarbageCollector()

        # Mock trigger manager
        with patch('apps.ai_core.ai_core.workers.garbage_collector.get_trigger_manager') as mock_tm:
            mock_tm.return_value = Mock()
            await gc._cleanup_pending_agents(session_factory, temp_dir)

        # Verify agent1 still exists
        assert repo.get_by_id(agent1.id) is not None

        # Verify agent2 is deleted (need to use include_pending_deletion to check)
        agents = repo.list_all(include_pending_deletion=True)
        agent_ids = [a.id for a in agents]
        assert agent1.id in agent_ids
        assert agent2.id not in agent_ids

        # Verify directory is deleted
        assert not os.path.exists(agent2_dir)

    @pytest.mark.asyncio
    async def test_cleanup_handles_missing_directory(self, session_factory, temp_dir, db_session):
        """Test cleanup handles agent with no directory gracefully."""
        repo = AgentRepository(db_session)

        # Create agent without creating directory
        agent = repo.create(name="No Dir Agent")
        repo.mark_for_deletion(agent.id)

        gc = AgentGarbageCollector()

        with patch('apps.ai_core.ai_core.workers.garbage_collector.get_trigger_manager') as mock_tm:
            mock_tm.return_value = Mock()
            # Should not raise exception
            await gc._cleanup_pending_agents(session_factory, temp_dir)

        # Agent should still be deleted from DB
        assert repo.get_by_id(agent.id) is None

    @pytest.mark.asyncio
    async def test_cleanup_deletes_drafts(self, session_factory, temp_dir, db_session):
        """Test that cleanup also deletes agent drafts."""
        agent_repo = AgentRepository(db_session)
        draft_repo = AgentDraftRepository(db_session)

        # Create agent with drafts
        agent = agent_repo.create(name="Agent with Drafts")
        draft_repo.create(
            agent_id=agent.id,
            name="Draft 1",
            file_path="d1.json",
            base_version=1
        )
        draft_repo.create(
            agent_id=agent.id,
            name="Draft 2",
            file_path="d2.json",
            base_version=1
        )

        # Mark for deletion
        agent_repo.mark_for_deletion(agent.id)

        gc = AgentGarbageCollector()

        with patch('apps.ai_core.ai_core.workers.garbage_collector.get_trigger_manager') as mock_tm:
            mock_tm.return_value = Mock()
            await gc._cleanup_pending_agents(session_factory, temp_dir)

        # Drafts should be deleted (via cascade)
        assert draft_repo.count_by_agent(agent.id) == 0

    @pytest.mark.asyncio
    async def test_cleanup_calls_trigger_manager(self, session_factory, temp_dir, db_session):
        """Test that cleanup unregisters triggers."""
        repo = AgentRepository(db_session)
        agent = repo.create(name="Agent with Triggers")
        repo.mark_for_deletion(agent.id)

        gc = AgentGarbageCollector()

        with patch('apps.ai_core.ai_core.workers.garbage_collector.get_trigger_manager') as mock_tm:
            mock_trigger_manager = Mock()
            mock_tm.return_value = mock_trigger_manager

            await gc._cleanup_pending_agents(session_factory, temp_dir)

            # Verify trigger manager was called
            mock_trigger_manager.unregister_triggers_for_agent.assert_called_once_with(agent.id)

    @pytest.mark.asyncio
    async def test_cleanup_continues_on_individual_error(self, session_factory, temp_dir, db_session):
        """Test that cleanup continues even if one agent fails."""
        repo = AgentRepository(db_session)

        agent1 = repo.create(name="Agent 1")
        agent2 = repo.create(name="Agent 2")

        repo.mark_for_deletion(agent1.id)
        repo.mark_for_deletion(agent2.id)

        gc = AgentGarbageCollector()

        # Make trigger manager fail for first agent but succeed for second
        call_count = [0]

        def mock_unregister(agent_id):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated error")

        with patch('apps.ai_core.ai_core.workers.garbage_collector.get_trigger_manager') as mock_tm:
            mock_trigger_manager = Mock()
            mock_trigger_manager.unregister_triggers_for_agent.side_effect = mock_unregister
            mock_tm.return_value = mock_trigger_manager

            # Should not raise, should continue processing
            await gc._cleanup_pending_agents(session_factory, temp_dir)

            # Both agents should have been attempted
            assert mock_trigger_manager.unregister_triggers_for_agent.call_count == 2


@pytest.mark.skip(reason="Async worker tests require additional setup for database fixtures")
class TestAgentGarbageCollectorRunLoop:
    """Test GarbageCollector async run loop."""

    @pytest.mark.asyncio
    async def test_run_can_be_cancelled(self):
        """Test that run loop can be cancelled."""
        gc = AgentGarbageCollector(interval_seconds=1)

        session_factory = Mock()
        data_root = "/tmp/test"

        # Start the run loop
        task = asyncio.create_task(gc.run(session_factory, data_root))

        # Cancel after a short delay
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have stopped
        assert gc._running is False or task.cancelled()

    @pytest.mark.asyncio
    async def test_run_continues_after_error(self):
        """Test that run loop continues after error in cleanup."""
        gc = AgentGarbageCollector(interval_seconds=0.1)

        error_count = [0]

        async def mock_cleanup(*args):
            error_count[0] += 1
            if error_count[0] <= 2:
                raise Exception("Test error")

        gc._cleanup_pending_agents = mock_cleanup

        session_factory = Mock()

        # Start and let it run for a bit
        task = asyncio.create_task(gc.run(session_factory, "/tmp"))

        await asyncio.sleep(0.5)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have retried multiple times despite errors
        assert error_count[0] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
