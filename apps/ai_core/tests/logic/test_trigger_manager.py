# apps/ai_core/tests/logic/test_trigger_manager.py
"""
Unit tests for TriggerManager - basic tests.

Note: Comprehensive tests are in tests/test_trigger_manager.py and
tests/test_trigger_integration.py. This file contains minimal tests
to ensure the module loads correctly.
"""

import pytest

from ai_core.logic.trigger_manager import (
    TriggerManager,
    get_trigger_manager,
    TriggerStatus,
    TriggerConfig,
    compute_config_hash
)


class TestTriggerManagerSingleton:
    """Test TriggerManager singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before and after each test."""
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

    def test_get_trigger_manager_returns_instance(self):
        """Test that get_trigger_manager returns a TriggerManager instance."""
        manager = get_trigger_manager()
        assert isinstance(manager, TriggerManager)

    def test_singleton_returns_same_instance(self):
        """Test that multiple calls return the same instance."""
        manager1 = get_trigger_manager()
        manager2 = get_trigger_manager()
        assert manager1 is manager2


class TestTriggerValidation:
    """Test trigger configuration validation."""

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
            {"type": "webhook", "endpoint": "/hook"}
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


class TestConfigHash:
    """Test config hash computation."""

    def test_same_config_same_hash(self):
        """Same config should produce same hash."""
        config1 = {"schedule": "* * * * *"}
        config2 = {"schedule": "* * * * *"}
        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_different_config_different_hash(self):
        """Different config should produce different hash."""
        config1 = {"schedule": "* * * * *"}
        config2 = {"schedule": "0 * * * *"}
        assert compute_config_hash(config1) != compute_config_hash(config2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
