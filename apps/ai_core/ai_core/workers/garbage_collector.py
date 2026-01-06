# apps/ai_core/ai_core/workers/garbage_collector.py
"""
AgentGarbageCollector - Background worker for cleaning up deleted agents.

This worker periodically scans for agents marked for deletion (deletion_status='PENDING')
and performs physical cleanup:
- Unregisters triggers
- Deletes agent folder from filesystem
- Deletes database records (agent_drafts, agent_test_cases, agents)
"""

import asyncio
import shutil
import logging
from typing import Callable
from pathlib import Path

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AgentGarbageCollector:
    """
    Background worker that cleans up agents marked for deletion.

    Runs as an asyncio task and periodically scans for pending deletions.
    """

    def __init__(self, interval_seconds: int = 300):
        """
        Initialize the garbage collector.

        Args:
            interval_seconds: How often to run cleanup (default: 5 minutes)
        """
        self.interval = interval_seconds
        self._running = False
        self._task = None

    async def run(self, session_factory: Callable[[], Session], data_root: str):
        """
        Main loop for the garbage collector.

        Args:
            session_factory: Callable that creates a new database session
            data_root: Path to DATA_ROOT where agent files are stored
        """
        self._running = True
        logger.info(f"AgentGarbageCollector started (interval: {self.interval}s)")

        while self._running:
            try:
                await asyncio.sleep(self.interval)
                await self._cleanup_pending_agents(session_factory, data_root)
            except asyncio.CancelledError:
                logger.info("AgentGarbageCollector received cancel signal")
                break
            except Exception as e:
                logger.error(f"AgentGarbageCollector error: {e}")
                # Continue running despite errors

        logger.info("AgentGarbageCollector stopped")

    def stop(self):
        """Signal the worker to stop."""
        self._running = False

    async def _cleanup_pending_agents(self, session_factory: Callable[[], Session],
                                       data_root: str):
        """
        Find and clean up agents pending deletion.

        Args:
            session_factory: Callable that creates a new database session
            data_root: Path to DATA_ROOT
        """
        session = session_factory()

        try:
            from apps.ai_core.ai_core.db.repositories import (
                AgentRepository, AgentDraftRepository, AgentTestCaseRepository
            )
            from apps.ai_core.ai_core.logic.trigger_manager import get_trigger_manager

            agent_repo = AgentRepository(session)
            pending_agents = agent_repo.list_pending_deletion()

            if not pending_agents:
                return

            logger.info(f"Found {len(pending_agents)} agent(s) pending deletion")

            trigger_manager = get_trigger_manager()
            draft_repo = AgentDraftRepository(session)
            test_case_repo = AgentTestCaseRepository(session)

            for agent in pending_agents:
                agent_id = agent.id

                try:
                    logger.info(f"Cleaning up agent {agent_id}...")

                    # 1. Unregister triggers (best-effort)
                    try:
                        trigger_manager.unregister_triggers_for_agent(agent_id)
                    except Exception as e:
                        logger.warning(f"Failed to unregister triggers for {agent_id}: {e}")

                    # 2. Delete filesystem folder
                    agent_folder = Path(data_root) / agent_id
                    if agent_folder.exists():
                        try:
                            shutil.rmtree(agent_folder, ignore_errors=True)
                            logger.debug(f"Deleted folder: {agent_folder}")
                        except Exception as e:
                            logger.warning(f"Failed to delete folder {agent_folder}: {e}")

                    # 3. Delete database records (cascading through relationships)
                    # Drafts
                    draft_repo.delete_by_agent(agent_id)

                    # Test cases are deleted via cascade, but we can be explicit
                    # (Note: ORM cascade should handle this)

                    # Finally, delete the agent
                    agent_repo.hard_delete(agent_id)

                    logger.info(f"Agent {agent_id} cleanup complete")

                except Exception as e:
                    logger.error(f"Error cleaning up agent {agent_id}: {e}")
                    # Continue with next agent

        finally:
            session.close()


# Global instance
_garbage_collector: AgentGarbageCollector = None


def get_garbage_collector() -> AgentGarbageCollector:
    """Get the global garbage collector instance."""
    global _garbage_collector
    if _garbage_collector is None:
        _garbage_collector = AgentGarbageCollector()
    return _garbage_collector


def init_garbage_collector(interval_seconds: int = 300) -> AgentGarbageCollector:
    """Initialize the global garbage collector instance."""
    global _garbage_collector
    _garbage_collector = AgentGarbageCollector(interval_seconds)
    return _garbage_collector
