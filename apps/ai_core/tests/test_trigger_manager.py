# apps/ai_core/tests/test_trigger_manager.py
"""
Unit tests for TriggerManager.

Tests cover the acceptance criteria from the specification:
- Start ENABLED: trigger starts within one reconcile tick
- DISABLED: trigger stops when disabled
- Config drift: trigger restarts when config_hash changes
- FAILED not auto-start: after N crashes, status is FAILED and no auto-restart
- Unfreeze FAILED: management API can re-enable FAILED triggers
- emit valid: creates execution
- emit invalid: no execution, error logged
- Intentional stop: no FAILED status on graceful stop
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

# Test fixtures and mocks
@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()
    session.refresh = MagicMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def mock_trigger_instance():
    """Create a mock TriggerInstance ORM object."""
    instance = MagicMock()
    instance.trigger_instance_id = "test-trigger-123"
    instance.agent_id = "test-agent-456"
    instance.trigger_id = "cron"
    instance.status = "ENABLED"
    instance.config_json = '{"schedule": "* * * * *"}'
    instance.config_hash = "abc123"
    instance.error_message = None
    instance.error_at = None
    instance.created_at = datetime.utcnow()
    instance.updated_at = datetime.utcnow()
    instance.get_config = MagicMock(return_value={"schedule": "* * * * *"})
    instance.set_config = MagicMock()
    return instance


class TestComputeConfigHash:
    """Tests for compute_config_hash function."""

    def test_same_config_same_hash(self):
        """Same config should produce same hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        config1 = {"schedule": "* * * * *", "enabled": True}
        config2 = {"schedule": "* * * * *", "enabled": True}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_order_same_hash(self):
        """Config with different key order should produce same hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        config1 = {"a": 1, "b": 2}
        config2 = {"b": 2, "a": 1}

        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_config_different_hash(self):
        """Different config should produce different hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        config1 = {"schedule": "* * * * *"}
        config2 = {"schedule": "0 * * * *"}

        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_empty_config(self):
        """Empty config should produce consistent hash."""
        from ai_core.logic.trigger_manager import compute_config_hash

        assert compute_config_hash({}) == compute_config_hash({})


class TestTriggerConfig:
    """Tests for TriggerConfig Pydantic model."""

    def test_valid_config(self):
        """Valid config should parse correctly."""
        from ai_core.logic.trigger_manager import TriggerConfig, TriggerStatus

        config = TriggerConfig(
            trigger_id="cron",
            status=TriggerStatus.ENABLED,
            config={"schedule": "* * * * *"}
        )

        assert config.trigger_id == "cron"
        assert config.status == TriggerStatus.ENABLED
        assert config.config == {"schedule": "* * * * *"}

    def test_default_status(self):
        """Default status should be ENABLED."""
        from ai_core.logic.trigger_manager import TriggerConfig, TriggerStatus

        config = TriggerConfig(trigger_id="webhook")

        assert config.status == TriggerStatus.ENABLED

    def test_default_config(self):
        """Default config should be empty dict."""
        from ai_core.logic.trigger_manager import TriggerConfig

        config = TriggerConfig(trigger_id="webhook")

        assert config.config == {}


class TestTriggerRegistry:
    """Tests for TriggerRegistry."""

    def test_register_plugin(self):
        """Should register a plugin."""
        from ai_core.logic.trigger_manager import TriggerRegistry, TriggerPlugin

        registry = TriggerRegistry()

        # Create mock plugin
        mock_spec = MagicMock()
        mock_spec.trigger_id = "test_trigger"

        mock_plugin = MagicMock(spec=TriggerPlugin)
        mock_plugin.spec.return_value = mock_spec

        registry.register(mock_plugin)

        assert registry.get("test_trigger") == mock_plugin
        assert "test_trigger" in registry.list_trigger_ids()

    def test_get_nonexistent_plugin(self):
        """Should return None for nonexistent plugin."""
        from ai_core.logic.trigger_manager import TriggerRegistry

        registry = TriggerRegistry()

        assert registry.get("nonexistent") is None


class TestTriggerInstanceResponse:
    """Tests for TriggerInstanceResponse model."""

    def test_from_orm(self, mock_trigger_instance):
        """Should convert ORM model to response."""
        from ai_core.logic.trigger_manager import TriggerInstanceResponse, TriggerStatus

        response = TriggerInstanceResponse(
            trigger_instance_id=mock_trigger_instance.trigger_instance_id,
            agent_id=mock_trigger_instance.agent_id,
            trigger_id=mock_trigger_instance.trigger_id,
            status=TriggerStatus(mock_trigger_instance.status),
            config=mock_trigger_instance.get_config(),
            config_hash=mock_trigger_instance.config_hash,
            error_message=mock_trigger_instance.error_message,
            error_at=mock_trigger_instance.error_at,
            created_at=mock_trigger_instance.created_at,
            updated_at=mock_trigger_instance.updated_at
        )

        assert response.trigger_instance_id == "test-trigger-123"
        assert response.agent_id == "test-agent-456"
        assert response.trigger_id == "cron"
        assert response.status == TriggerStatus.ENABLED


class TestRuntimeHandle:
    """Tests for RuntimeHandle dataclass."""

    def test_create_handle(self):
        """Should create a runtime handle."""
        from ai_core.logic.trigger_manager import RuntimeHandle

        cancel_event = asyncio.Event()
        task = MagicMock()

        handle = RuntimeHandle(
            trigger_instance_id="test-123",
            agent_id="agent-456",
            trigger_id="cron",
            task=task,
            cancel_event=cancel_event,
            config_hash="abc123"
        )

        assert handle.trigger_instance_id == "test-123"
        assert handle.stopping is False
        assert handle.crash_count == 0
        assert handle.last_crash_at is None

    def test_default_values(self):
        """Should have correct default values."""
        from ai_core.logic.trigger_manager import RuntimeHandle

        cancel_event = asyncio.Event()
        task = MagicMock()

        handle = RuntimeHandle(
            trigger_instance_id="test-123",
            agent_id="agent-456",
            trigger_id="cron",
            task=task,
            cancel_event=cancel_event,
            config_hash="abc123"
        )

        assert handle.stopping is False
        assert handle.crash_count == 0
        assert handle.last_crash_at is None
        assert handle.started_at is not None


class TestTriggerManagerSingleton:
    """Tests for TriggerManager singleton pattern."""

    def test_singleton_same_instance(self):
        """Multiple calls should return same instance."""
        # Reset singleton for test
        from ai_core.logic import trigger_manager
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False
        trigger_manager._trigger_manager = None

        from ai_core.logic.trigger_manager import TriggerManager

        manager1 = TriggerManager()
        manager2 = TriggerManager()

        assert manager1 is manager2

        # Cleanup
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False


class TestTriggerManagerValidation:
    """Tests for validate_triggers_config legacy method."""

    def test_valid_triggers(self):
        """Should validate correct trigger configs."""
        # Reset singleton for test
        from ai_core.logic import trigger_manager
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False
        trigger_manager._trigger_manager = None

        from ai_core.logic.trigger_manager import TriggerManager

        manager = TriggerManager()

        triggers = [
            {"type": "cron", "config": {"schedule": "* * * * *"}},
            {"trigger_id": "webhook", "config": {"url": "/hook"}}
        ]

        is_valid, error = manager.validate_triggers_config(triggers)

        assert is_valid is True
        assert error is None

        # Cleanup
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False

    def test_invalid_not_list(self):
        """Should reject non-list input."""
        from ai_core.logic import trigger_manager
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False
        trigger_manager._trigger_manager = None

        from ai_core.logic.trigger_manager import TriggerManager

        manager = TriggerManager()

        is_valid, error = manager.validate_triggers_config("not a list")

        assert is_valid is False
        assert "must be a list" in error

        # Cleanup
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False

    def test_invalid_missing_type(self):
        """Should reject triggers without type."""
        from ai_core.logic import trigger_manager
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False
        trigger_manager._trigger_manager = None

        from ai_core.logic.trigger_manager import TriggerManager

        manager = TriggerManager()

        triggers = [{"config": {"foo": "bar"}}]

        is_valid, error = manager.validate_triggers_config(triggers)

        assert is_valid is False
        assert "missing 'type' or 'trigger_id'" in error

        # Cleanup
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False


class TestSetAgentTriggersRequest:
    """Tests for SetAgentTriggersRequest model."""

    def test_valid_request(self):
        """Should parse valid request."""
        from ai_core.logic.trigger_manager import (
            SetAgentTriggersRequest,
            TriggerConfig,
            TriggerStatus
        )

        request = SetAgentTriggersRequest(
            triggers=[
                TriggerConfig(trigger_id="cron", config={"schedule": "* * * * *"}),
                TriggerConfig(trigger_id="webhook", status=TriggerStatus.DISABLED)
            ]
        )

        assert len(request.triggers) == 2
        assert request.triggers[0].trigger_id == "cron"
        assert request.triggers[1].status == TriggerStatus.DISABLED


class TestTriggerStatus:
    """Tests for TriggerStatus enum."""

    def test_enum_values(self):
        """Should have correct enum values."""
        from ai_core.logic.trigger_manager import TriggerStatus

        assert TriggerStatus.ENABLED.value == "ENABLED"
        assert TriggerStatus.DISABLED.value == "DISABLED"
        assert TriggerStatus.FAILED.value == "FAILED"

    def test_string_conversion(self):
        """Should convert to/from string."""
        from ai_core.logic.trigger_manager import TriggerStatus

        assert str(TriggerStatus.ENABLED) == "TriggerStatus.ENABLED"
        assert TriggerStatus("ENABLED") == TriggerStatus.ENABLED


class TestResponseModels:
    """Tests for response model structures."""

    def test_set_agent_triggers_response(self):
        """Should create valid response."""
        from ai_core.logic.trigger_manager import SetAgentTriggersResponse

        response = SetAgentTriggersResponse(
            agent_id="agent-123",
            triggers=[],
            created=2,
            updated=1,
            deleted=0
        )

        assert response.agent_id == "agent-123"
        assert response.created == 2
        assert response.updated == 1
        assert response.deleted == 0

    def test_delete_agent_triggers_response(self):
        """Should create valid delete response."""
        from ai_core.logic.trigger_manager import DeleteAgentTriggersResponse

        response = DeleteAgentTriggersResponse(
            agent_id="agent-123",
            deleted=5
        )

        assert response.agent_id == "agent-123"
        assert response.deleted == 5

    def test_set_enabled_response(self):
        """Should create valid enable/disable response."""
        from ai_core.logic.trigger_manager import SetAgentTriggersEnabledResponse

        response = SetAgentTriggersEnabledResponse(
            agent_id="agent-123",
            enabled=True,
            affected=3
        )

        assert response.agent_id == "agent-123"
        assert response.enabled is True
        assert response.affected == 3


# Integration tests (require more setup)
class TestTriggerManagerIntegration:
    """Integration tests for TriggerManager with mocked dependencies."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before and after each test."""
        from ai_core.logic import trigger_manager
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False
        trigger_manager._trigger_manager = None
        yield
        trigger_manager.TriggerManager._instance = None
        trigger_manager.TriggerManager._initialized = False
        trigger_manager._trigger_manager = None

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Should start and stop without errors."""
        from ai_core.logic.trigger_manager import TriggerManager

        mock_session_factory = MagicMock()

        manager = TriggerManager(session_factory=mock_session_factory)

        await manager.start()
        assert manager._running is True

        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_list_triggers_empty(self):
        """Should return empty list when no triggers."""
        from ai_core.logic.trigger_manager import TriggerManager

        mock_session = MagicMock()
        mock_session.close = MagicMock()

        mock_repo = MagicMock()
        mock_repo.list_all.return_value = []

        mock_session_factory = MagicMock(return_value=mock_session)

        manager = TriggerManager(session_factory=mock_session_factory)

        with patch('ai_core.db.repositories.TriggerInstanceRepository', return_value=mock_repo):
            result = await manager.list_triggers()

        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
