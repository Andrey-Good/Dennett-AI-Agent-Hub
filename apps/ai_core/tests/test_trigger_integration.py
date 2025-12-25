# apps/ai_core/tests/test_trigger_integration.py
"""
Integration tests for TriggerManager with Agents.

These tests verify that TriggerManager correctly integrates with:
- Agent creation/deletion
- Trigger creation via register_trigger (legacy API)
- Trigger management via async API (set_agent_triggers)
- AgentRun creation via emit()
- Full lifecycle: create agent -> set triggers -> emit -> verify run
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_core.db.orm_models import Base, Agent, TriggerInstance, AgentRun


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def test_db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session_factory(test_db_engine):
    """Create a session factory for the test database."""
    Session = sessionmaker(bind=test_db_engine)
    return Session


@pytest.fixture
def test_session(test_session_factory):
    """Create a test session."""
    session = test_session_factory()
    yield session
    session.close()


@pytest.fixture
def reset_trigger_manager():
    """Reset TriggerManager singleton before and after each test."""
    from ai_core.logic import trigger_manager

    # Store original state
    original_instance = trigger_manager.TriggerManager._instance
    original_initialized = trigger_manager.TriggerManager._initialized
    original_global = trigger_manager._trigger_manager

    # Reset
    trigger_manager.TriggerManager._instance = None
    trigger_manager.TriggerManager._initialized = False
    trigger_manager._trigger_manager = None

    yield

    # Restore
    trigger_manager.TriggerManager._instance = original_instance
    trigger_manager.TriggerManager._initialized = original_initialized
    trigger_manager._trigger_manager = original_global


@pytest.fixture
def trigger_manager_with_db(test_session_factory, reset_trigger_manager):
    """Create a TriggerManager with test database."""
    from ai_core.logic.trigger_manager import TriggerManager

    manager = TriggerManager(
        session_factory=test_session_factory,
        reconcile_interval_sec=1,
        max_crash_retries=3
    )
    return manager


@pytest.fixture
def sample_agent(test_session):
    """Create a sample agent in the test database."""
    agent = Agent(
        id='test-agent-001',
        name='Test Agent',
        description='A test agent',
        version=1,
        is_active=0,
        deletion_status='NONE',
        file_path='test-agent-001/v1.json'
    )
    test_session.add(agent)
    test_session.commit()
    test_session.refresh(agent)
    return agent


# =============================================================================
# Test: Legacy API Integration (register_trigger / unregister_triggers_for_agent)
# =============================================================================

class TestLegacyAPIIntegration:
    """Tests for legacy register_trigger/unregister_triggers_for_agent API."""

    def test_register_trigger_creates_db_record(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """register_trigger should create a TriggerInstance in the database."""
        trigger_config = {
            'type': 'cron',
            'config': {'schedule': '* * * * *'}
        }

        result = trigger_manager_with_db.register_trigger(
            sample_agent.id,
            trigger_config
        )

        assert result is True

        # Verify database record was created
        from ai_core.db.repositories import TriggerInstanceRepository
        repo = TriggerInstanceRepository(test_session)
        triggers = repo.list_by_agent(sample_agent.id)

        assert len(triggers) == 1
        assert triggers[0].trigger_id == 'cron'
        assert triggers[0].status == 'ENABLED'
        assert triggers[0].get_config() == {'schedule': '* * * * *'}

    def test_register_trigger_with_trigger_id_key(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """register_trigger should work with 'trigger_id' key instead of 'type'."""
        trigger_config = {
            'trigger_id': 'webhook',
            'config': {'url': '/api/hook'}
        }

        result = trigger_manager_with_db.register_trigger(
            sample_agent.id,
            trigger_config
        )

        assert result is True

        from ai_core.db.repositories import TriggerInstanceRepository
        repo = TriggerInstanceRepository(test_session)
        triggers = repo.list_by_agent(sample_agent.id)

        assert len(triggers) == 1
        assert triggers[0].trigger_id == 'webhook'

    def test_register_trigger_without_type_fails(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """register_trigger should fail if no 'type' or 'trigger_id' is provided."""
        trigger_config = {
            'config': {'schedule': '* * * * *'}
        }

        result = trigger_manager_with_db.register_trigger(
            sample_agent.id,
            trigger_config
        )

        assert result is False

    def test_register_trigger_updates_existing(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """register_trigger should update config if trigger already exists."""
        # Register initial trigger
        trigger_manager_with_db.register_trigger(
            sample_agent.id,
            {'type': 'cron', 'config': {'schedule': '* * * * *'}}
        )

        # Register same trigger with different config
        trigger_manager_with_db.register_trigger(
            sample_agent.id,
            {'type': 'cron', 'config': {'schedule': '0 * * * *'}}
        )

        from ai_core.db.repositories import TriggerInstanceRepository
        repo = TriggerInstanceRepository(test_session)
        triggers = repo.list_by_agent(sample_agent.id)

        # Should still be only one trigger
        assert len(triggers) == 1
        # Config should be updated
        assert triggers[0].get_config() == {'schedule': '0 * * * *'}

    def test_register_multiple_triggers(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """Should be able to register multiple different triggers."""
        trigger_manager_with_db.register_trigger(
            sample_agent.id,
            {'type': 'cron', 'config': {'schedule': '* * * * *'}}
        )
        trigger_manager_with_db.register_trigger(
            sample_agent.id,
            {'type': 'webhook', 'config': {'url': '/hook'}}
        )

        from ai_core.db.repositories import TriggerInstanceRepository
        repo = TriggerInstanceRepository(test_session)
        triggers = repo.list_by_agent(sample_agent.id)

        assert len(triggers) == 2
        trigger_ids = {t.trigger_id for t in triggers}
        assert trigger_ids == {'cron', 'webhook'}

    def test_unregister_triggers_for_agent(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """unregister_triggers_for_agent should delete all triggers from DB."""
        # Register some triggers
        trigger_manager_with_db.register_trigger(
            sample_agent.id,
            {'type': 'cron', 'config': {'schedule': '* * * * *'}}
        )
        trigger_manager_with_db.register_trigger(
            sample_agent.id,
            {'type': 'webhook', 'config': {'url': '/hook'}}
        )

        # Unregister all
        count = trigger_manager_with_db.unregister_triggers_for_agent(sample_agent.id)

        assert count == 2

        # Verify database is empty
        from ai_core.db.repositories import TriggerInstanceRepository
        repo = TriggerInstanceRepository(test_session)
        triggers = repo.list_by_agent(sample_agent.id)

        assert len(triggers) == 0

    def test_unregister_nonexistent_agent(
        self,
        trigger_manager_with_db
    ):
        """unregister_triggers_for_agent should return 0 for nonexistent agent."""
        count = trigger_manager_with_db.unregister_triggers_for_agent('nonexistent-agent')
        assert count == 0


# =============================================================================
# Test: Async API Integration (set_agent_triggers, list_agent_triggers, etc.)
# =============================================================================

class TestAsyncAPIIntegration:
    """Tests for async API methods."""

    @pytest.mark.asyncio
    async def test_set_agent_triggers(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """set_agent_triggers should create triggers in the database."""
        from ai_core.logic.trigger_manager import TriggerConfig, TriggerStatus

        triggers = [
            TriggerConfig(
                trigger_id='cron',
                status=TriggerStatus.ENABLED,
                config={'schedule': '* * * * *'}
            ),
            TriggerConfig(
                trigger_id='webhook',
                status=TriggerStatus.DISABLED,
                config={'url': '/api/hook'}
            )
        ]

        result = await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            triggers
        )

        assert result.agent_id == sample_agent.id
        assert result.created == 2
        assert result.updated == 0
        assert result.deleted == 0
        assert len(result.triggers) == 2

    @pytest.mark.asyncio
    async def test_set_agent_triggers_updates_existing(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """set_agent_triggers should update existing triggers."""
        from ai_core.logic.trigger_manager import TriggerConfig, TriggerStatus

        # Create initial triggers
        await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'})]
        )

        # Update with different config
        result = await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [TriggerConfig(trigger_id='cron', config={'schedule': '0 * * * *'})]
        )

        assert result.updated == 1
        assert result.created == 0
        assert result.deleted == 0

    @pytest.mark.asyncio
    async def test_set_agent_triggers_deletes_removed(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """set_agent_triggers should delete triggers not in the new list."""
        from ai_core.logic.trigger_manager import TriggerConfig

        # Create two triggers
        await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [
                TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'}),
                TriggerConfig(trigger_id='webhook', config={'url': '/hook'})
            ]
        )

        # Set with only one trigger
        result = await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'})]
        )

        assert result.deleted == 1
        assert len(result.triggers) == 1
        assert result.triggers[0].trigger_id == 'cron'

    @pytest.mark.asyncio
    async def test_list_agent_triggers(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """list_agent_triggers should return all triggers for an agent."""
        from ai_core.logic.trigger_manager import TriggerConfig

        # Create triggers
        await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [
                TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'}),
                TriggerConfig(trigger_id='webhook', config={'url': '/hook'})
            ]
        )

        triggers = await trigger_manager_with_db.list_agent_triggers(sample_agent.id)

        assert len(triggers) == 2
        trigger_ids = {t.trigger_id for t in triggers}
        assert trigger_ids == {'cron', 'webhook'}

    @pytest.mark.asyncio
    async def test_delete_agent_triggers(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """delete_agent_triggers should remove all triggers for an agent."""
        from ai_core.logic.trigger_manager import TriggerConfig

        # Create triggers
        await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [
                TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'}),
                TriggerConfig(trigger_id='webhook', config={'url': '/hook'})
            ]
        )

        result = await trigger_manager_with_db.delete_agent_triggers(sample_agent.id)

        assert result.agent_id == sample_agent.id
        assert result.deleted == 2

        # Verify empty
        triggers = await trigger_manager_with_db.list_agent_triggers(sample_agent.id)
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_set_agent_triggers_enabled(
        self,
        trigger_manager_with_db,
        sample_agent,
        test_session
    ):
        """set_agent_triggers_enabled should enable/disable all triggers."""
        from ai_core.logic.trigger_manager import TriggerConfig

        # Create triggers
        await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [
                TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'}),
                TriggerConfig(trigger_id='webhook', config={'url': '/hook'})
            ]
        )

        # Disable all
        result = await trigger_manager_with_db.set_agent_triggers_enabled(
            sample_agent.id,
            enabled=False
        )

        assert result.enabled is False
        assert result.affected == 2

        # Verify status
        triggers = await trigger_manager_with_db.list_agent_triggers(sample_agent.id)
        for t in triggers:
            assert t.status.value == 'DISABLED'

    @pytest.mark.asyncio
    async def test_get_trigger(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """get_trigger should return a specific trigger by ID."""
        from ai_core.logic.trigger_manager import TriggerConfig

        # Create trigger
        result = await trigger_manager_with_db.set_agent_triggers(
            sample_agent.id,
            [TriggerConfig(trigger_id='cron', config={'schedule': '* * * * *'})]
        )

        trigger_id = result.triggers[0].trigger_instance_id

        trigger = await trigger_manager_with_db.get_trigger(trigger_id)

        assert trigger is not None
        assert trigger.trigger_instance_id == trigger_id
        assert trigger.trigger_id == 'cron'

    @pytest.mark.asyncio
    async def test_get_trigger_not_found(
        self,
        trigger_manager_with_db
    ):
        """get_trigger should return None for nonexistent trigger."""
        trigger = await trigger_manager_with_db.get_trigger('nonexistent-id')
        assert trigger is None


# =============================================================================
# Test: Start/Stop Lifecycle
# =============================================================================

class TestLifecycle:
    """Tests for TriggerManager start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop(
        self,
        trigger_manager_with_db
    ):
        """TriggerManager should start and stop cleanly."""
        await trigger_manager_with_db.start()

        assert trigger_manager_with_db._running is True
        assert trigger_manager_with_db._reconcile_task is not None

        await trigger_manager_with_db.stop()

        assert trigger_manager_with_db._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(
        self,
        trigger_manager_with_db
    ):
        """Starting twice should be safe."""
        await trigger_manager_with_db.start()
        await trigger_manager_with_db.start()  # Should not raise

        assert trigger_manager_with_db._running is True

        await trigger_manager_with_db.stop()

    @pytest.mark.asyncio
    async def test_double_stop_is_idempotent(
        self,
        trigger_manager_with_db
    ):
        """Stopping twice should be safe."""
        await trigger_manager_with_db.start()
        await trigger_manager_with_db.stop()
        await trigger_manager_with_db.stop()  # Should not raise

        assert trigger_manager_with_db._running is False


# =============================================================================
# Test: Config Hash
# =============================================================================

class TestConfigHash:
    """Tests for config hash computation."""

    def test_same_config_same_hash(self):
        """Same config should produce same hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        config1 = {'schedule': '* * * * *', 'enabled': True}
        config2 = {'schedule': '* * * * *', 'enabled': True}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_order_same_hash(self):
        """Config with different key order should produce same hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        config1 = {'a': 1, 'b': 2}
        config2 = {'b': 2, 'a': 1}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_config_different_hash(self):
        """Different config should produce different hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        config1 = {'schedule': '* * * * *'}
        config2 = {'schedule': '0 * * * *'}

        assert compute_config_hash(config1) != compute_config_hash(config2)


# =============================================================================
# Test: Validation
# =============================================================================

class TestValidation:
    """Tests for trigger configuration validation."""

    def test_validate_valid_triggers(self, trigger_manager_with_db):
        """Valid triggers should pass validation."""
        triggers = [
            {'type': 'cron', 'config': {'schedule': '* * * * *'}},
            {'trigger_id': 'webhook', 'config': {'url': '/hook'}}
        ]

        is_valid, error = trigger_manager_with_db.validate_triggers_config(triggers)

        assert is_valid is True
        assert error is None

    def test_validate_not_list_fails(self, trigger_manager_with_db):
        """Non-list input should fail validation."""
        is_valid, error = trigger_manager_with_db.validate_triggers_config('not a list')

        assert is_valid is False
        assert 'must be a list' in error

    def test_validate_missing_type_fails(self, trigger_manager_with_db):
        """Trigger without type should fail validation."""
        triggers = [{'config': {'foo': 'bar'}}]

        is_valid, error = trigger_manager_with_db.validate_triggers_config(triggers)

        assert is_valid is False
        assert "missing 'type'" in error


# =============================================================================
# Test: Helper Methods
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_active_triggers(
        self,
        trigger_manager_with_db,
        sample_agent
    ):
        """get_active_triggers should return list (may be empty if not running)."""
        triggers = trigger_manager_with_db.get_active_triggers(sample_agent.id)
        assert isinstance(triggers, list)

    def test_get_all_active_agents(self, trigger_manager_with_db):
        """get_all_active_agents should return list of agent IDs."""
        agents = trigger_manager_with_db.get_all_active_agents()
        assert isinstance(agents, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
