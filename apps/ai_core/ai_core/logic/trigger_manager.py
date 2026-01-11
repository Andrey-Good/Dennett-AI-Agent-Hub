# apps/ai_core/ai_core/logic/trigger_manager.py
"""
TriggerManager - Placeholder/Stub implementation.

This module provides a singleton TriggerManager for managing agent triggers.
Currently implemented as a stub that logs operations - full implementation
to be added later.

TriggerManager is responsible for:
- Registering triggers for agents (schedule, webhook, file_system, etc.)
- Unregistering triggers when agents are deactivated or deleted
- Validating trigger configurations before deployment
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TriggerManager:
    """
    Singleton manager for agent triggers.

    This is a stub implementation that logs all operations.
    Full implementation will handle:
    - asyncio.Task creation for schedule triggers
    - Webhook endpoint registration
    - File system watcher setup
    - Trigger state persistence in database
    """

    _instance: Optional['TriggerManager'] = None
    _initialized: bool = False

    def __new__(cls) -> 'TriggerManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if TriggerManager._initialized:
            return
        TriggerManager._initialized = True

        # In-memory registry of active triggers
        # Structure: {agent_id: [trigger_configs]}
        self._active_triggers: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("TriggerManager initialized (stub implementation)")

    def register_trigger(
        self,
        agent_id: str,
        trigger_config: Dict[str, Any]
    ) -> bool:
        """
        Register a trigger for an agent.

        Args:
            agent_id: UUID of the agent
            trigger_config: Trigger configuration dictionary containing:
                - type: Trigger type (schedule, webhook, file_system, etc.)
                - config: Type-specific configuration

        Returns:
            True if registration succeeded

        Note:
            STUB: Currently only logs the operation and stores in memory.
        """
        trigger_type = trigger_config.get('type', 'unknown')

        if agent_id not in self._active_triggers:
            self._active_triggers[agent_id] = []

        self._active_triggers[agent_id].append(trigger_config)

        logger.info(
            f"[STUB] Registered trigger for agent {agent_id}: "
            f"type={trigger_type}, config={trigger_config}"
        )
        return True

    def unregister_triggers_for_agent(self, agent_id: str) -> int:
        """
        Unregister all triggers for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            Number of triggers unregistered

        Note:
            STUB: Currently only logs the operation and clears memory.
        """
        triggers = self._active_triggers.pop(agent_id, [])
        count = len(triggers)

        if count > 0:
            logger.info(
                f"[STUB] Unregistered {count} trigger(s) for agent {agent_id}"
            )
        else:
            logger.debug(
                f"[STUB] No triggers to unregister for agent {agent_id}"
            )

        return count

    def validate_triggers_config(
        self,
        triggers: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate trigger configurations before deployment.

        Args:
            triggers: List of trigger configuration dictionaries

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if all triggers are valid
            - (False, "error description") if validation fails

        Note:
            STUB: Currently performs minimal validation.
        """
        if not isinstance(triggers, list):
            return False, "Triggers must be a list"

        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, dict):
                return False, f"Trigger at index {i} must be a dictionary"

            trigger_type = trigger.get('type')
            if not trigger_type:
                return False, f"Trigger at index {i} missing 'type' field"

            # Basic type validation
            valid_types = {'schedule', 'webhook', 'file_system', 'manual', 'event'}
            if trigger_type not in valid_types:
                logger.warning(
                    f"[STUB] Unknown trigger type '{trigger_type}' at index {i}, "
                    f"allowing for forward compatibility"
                )

        logger.debug(f"[STUB] Validated {len(triggers)} trigger config(s)")
        return True, None

    def get_active_triggers(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get list of active triggers for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            List of trigger configurations (empty if none)
        """
        return self._active_triggers.get(agent_id, []).copy()

    def get_all_active_agents(self) -> List[str]:
        """
        Get list of all agent IDs with active triggers.

        Returns:
            List of agent UUIDs
        """
        return list(self._active_triggers.keys())


# Global singleton instance
_trigger_manager: Optional[TriggerManager] = None


def get_trigger_manager() -> TriggerManager:
    """
    Get the global TriggerManager singleton instance.

    Returns:
        TriggerManager instance
    """
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = TriggerManager()
    return _trigger_manager
