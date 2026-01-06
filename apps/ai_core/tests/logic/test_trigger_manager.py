# apps/ai_core/tests/logic/test_trigger_manager.py
"""
Unit tests for TriggerManager stub implementation.

Tests the singleton pattern, trigger registration/unregistration,
and configuration validation.
"""

import pytest

from apps.ai_core.ai_core.logic.trigger_manager import (
    TriggerManager,
    get_trigger_manager
)


class TestTriggerManagerSingleton:
    """Test TriggerManager singleton pattern."""

    def test_get_trigger_manager_returns_instance(self):
        """Test that get_trigger_manager returns a TriggerManager instance."""
        manager = get_trigger_manager()
        assert isinstance(manager, TriggerManager)

    def test_singleton_returns_same_instance(self):
        """Test that multiple calls return the same instance."""
        manager1 = get_trigger_manager()
        manager2 = get_trigger_manager()
        assert manager1 is manager2

    def test_direct_instantiation_returns_same_instance(self):
        """Test that direct instantiation also returns the singleton."""
        manager1 = TriggerManager()
        manager2 = TriggerManager()
        assert manager1 is manager2


class TestTriggerRegistration:
    """Test trigger registration and unregistration."""

    @pytest.fixture(autouse=True)
    def clear_triggers(self):
        """Clear all triggers before each test."""
        manager = get_trigger_manager()
        # Clear the internal state
        manager._active_triggers.clear()
        yield
        manager._active_triggers.clear()

    def test_register_single_trigger(self):
        """Test registering a single trigger."""
        manager = get_trigger_manager()
        agent_id = "agent-123"
        trigger_config = {"type": "schedule", "cron": "0 * * * *"}

        result = manager.register_trigger(agent_id, trigger_config)

        assert result is True
        assert agent_id in manager._active_triggers
        assert len(manager._active_triggers[agent_id]) == 1
        assert manager._active_triggers[agent_id][0] == trigger_config

    def test_register_multiple_triggers_same_agent(self):
        """Test registering multiple triggers for the same agent."""
        manager = get_trigger_manager()
        agent_id = "agent-456"

        manager.register_trigger(agent_id, {"type": "schedule", "cron": "0 * * * *"})
        manager.register_trigger(agent_id, {"type": "webhook", "endpoint": "/hook"})
        manager.register_trigger(agent_id, {"type": "file_system", "path": "/data"})

        assert len(manager._active_triggers[agent_id]) == 3

    def test_register_triggers_different_agents(self):
        """Test registering triggers for different agents."""
        manager = get_trigger_manager()

        manager.register_trigger("agent-1", {"type": "schedule"})
        manager.register_trigger("agent-2", {"type": "webhook"})

        assert "agent-1" in manager._active_triggers
        assert "agent-2" in manager._active_triggers
        assert len(manager._active_triggers["agent-1"]) == 1
        assert len(manager._active_triggers["agent-2"]) == 1

    def test_unregister_triggers_for_agent(self):
        """Test unregistering all triggers for an agent."""
        manager = get_trigger_manager()
        agent_id = "agent-to-unregister"

        manager.register_trigger(agent_id, {"type": "schedule"})
        manager.register_trigger(agent_id, {"type": "webhook"})

        count = manager.unregister_triggers_for_agent(agent_id)

        assert count == 2
        assert agent_id not in manager._active_triggers

    def test_unregister_nonexistent_agent(self):
        """Test unregistering triggers for non-existent agent returns 0."""
        manager = get_trigger_manager()

        count = manager.unregister_triggers_for_agent("nonexistent-agent")

        assert count == 0

    def test_get_active_triggers(self):
        """Test getting active triggers for an agent."""
        manager = get_trigger_manager()
        agent_id = "agent-active"
        trigger1 = {"type": "schedule", "cron": "* * * * *"}
        trigger2 = {"type": "webhook", "path": "/api"}

        manager.register_trigger(agent_id, trigger1)
        manager.register_trigger(agent_id, trigger2)

        triggers = manager.get_active_triggers(agent_id)

        assert len(triggers) == 2
        assert trigger1 in triggers
        assert trigger2 in triggers

    def test_get_active_triggers_returns_copy(self):
        """Test that get_active_triggers returns a copy, not the original list."""
        manager = get_trigger_manager()
        agent_id = "agent-copy-test"

        manager.register_trigger(agent_id, {"type": "schedule"})
        triggers = manager.get_active_triggers(agent_id)

        # Modify the returned list
        triggers.append({"type": "fake"})

        # Original should be unchanged
        original = manager.get_active_triggers(agent_id)
        assert len(original) == 1

    def test_get_active_triggers_empty(self):
        """Test getting triggers for agent with no triggers returns empty list."""
        manager = get_trigger_manager()

        triggers = manager.get_active_triggers("no-triggers-agent")

        assert triggers == []

    def test_get_all_active_agents(self):
        """Test getting list of all agents with active triggers."""
        manager = get_trigger_manager()

        manager.register_trigger("agent-a", {"type": "schedule"})
        manager.register_trigger("agent-b", {"type": "webhook"})
        manager.register_trigger("agent-c", {"type": "file_system"})

        active_agents = manager.get_all_active_agents()

        assert len(active_agents) == 3
        assert "agent-a" in active_agents
        assert "agent-b" in active_agents
        assert "agent-c" in active_agents


class TestTriggerValidation:
    """Test trigger configuration validation."""

    def test_validate_empty_triggers_list(self):
        """Test validating an empty triggers list."""
        manager = get_trigger_manager()

        is_valid, error = manager.validate_triggers_config([])

        assert is_valid is True
        assert error is None

    def test_validate_valid_triggers(self):
        """Test validating valid trigger configurations."""
        manager = get_trigger_manager()
        triggers = [
            {"type": "schedule", "cron": "0 * * * *"},
            {"type": "webhook", "endpoint": "/hook"},
            {"type": "file_system", "path": "/data"}
        ]

        is_valid, error = manager.validate_triggers_config(triggers)

        assert is_valid is True
        assert error is None

    def test_validate_non_list_fails(self):
        """Test that non-list input fails validation."""
        manager = get_trigger_manager()

        is_valid, error = manager.validate_triggers_config({"type": "schedule"})

        assert is_valid is False
        assert "must be a list" in error

    def test_validate_non_dict_trigger_fails(self):
        """Test that non-dictionary trigger fails validation."""
        manager = get_trigger_manager()
        triggers = [
            {"type": "schedule"},
            "invalid-trigger"  # Not a dict
        ]

        is_valid, error = manager.validate_triggers_config(triggers)

        assert is_valid is False
        assert "must be a dictionary" in error

    def test_validate_missing_type_fails(self):
        """Test that trigger without type field fails validation."""
        manager = get_trigger_manager()
        triggers = [
            {"cron": "0 * * * *"}  # Missing 'type'
        ]

        is_valid, error = manager.validate_triggers_config(triggers)

        assert is_valid is False
        assert "missing 'type'" in error

    def test_validate_unknown_type_allowed(self):
        """Test that unknown trigger types are allowed (forward compatibility)."""
        manager = get_trigger_manager()
        triggers = [
            {"type": "future_trigger_type", "config": {}}
        ]

        is_valid, error = manager.validate_triggers_config(triggers)

        # Should still be valid (warning logged, but not an error)
        assert is_valid is True
        assert error is None

    def test_validate_all_known_types(self):
        """Test that all known trigger types are valid."""
        manager = get_trigger_manager()
        known_types = ['schedule', 'webhook', 'file_system', 'manual', 'event']

        for trigger_type in known_types:
            triggers = [{"type": trigger_type}]
            is_valid, error = manager.validate_triggers_config(triggers)
            assert is_valid is True, f"Type {trigger_type} should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
