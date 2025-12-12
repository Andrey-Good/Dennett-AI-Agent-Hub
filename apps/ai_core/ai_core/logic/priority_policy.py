import time
import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TaskSource(Enum):
    CHAT = "CHAT"
    CHAT_AGENT = "CHAT_AGENT"
    MANUAL_RUN = "MANUAL_RUN"
    INTERNAL_NODE = "INTERNAL_NODE"
    TRIGGER = "TRIGGER"


class PriorityPolicy_Base:
    """
    Base priority policy class (Community version).
    Implements Corridors, Inheritance, and Aging.
    Designed for inheritance by PriorityPolicy_Pro.

    This is the single source of truth for task prioritization.
    All tasks must pass through this "face control" before being queued.
    """
    def __init__(self, settings: Dict[str, Any]):
        # Priority Corridors
        default_corridors = {
            TaskSource.CHAT: 90,
            TaskSource.CHAT_AGENT: 90,
            TaskSource.MANUAL_RUN: 70,
            TaskSource.INTERNAL_NODE: 50,
            TaskSource.TRIGGER: 30,
        }
        self.base_priorities = settings.get("PRIORITY_CORRIDORS", default_corridors)

        # Aging Worker Parameters
        self.aging_interval_sec = settings.get("AGING_INTERVAL_SEC", 60)
        self.aging_threshold_sec = settings.get("AGING_THRESHOLD_SEC", 300)
        self.aging_boost = settings.get("AGING_BOOST", 10)
        self.aging_cap = settings.get("AGING_CAP_COMMUNITY", 65)

        logger.info(
            f"PriorityPolicy_Base initialized: "
            f"corridors={self.base_priorities}, "
            f"aging_cap={self.aging_cap}"
        )

    def assign_priority(
            self,
            source: TaskSource,
            parent_priority: Optional[int] = None,
            agent_config: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Assign priority to a task based on source and parent priority.

        Implements:
        - Mechanic 1: Priority Corridors
        - Mechanic 2: Priority Inheritance

        Args:
            source: Task source type (CHAT, MANUAL_RUN, etc.)
            parent_priority: Priority of parent task (if any)
            agent_config: Agent configuration (IGNORED in Base version, hook for Pro)

        Returns:
            Final priority value (higher = more important)
        """
        # Mechanic 1: Base priority from corridors
        base_priority = self.base_priorities.get(source, 30)  # 30 = default fallback

        # Mechanic 2: Priority inheritance to prevent inversion
        if parent_priority is not None:
            final_priority = max(base_priority, parent_priority)
        else:
            final_priority = base_priority

        # Hook for Pro: agent_config is intentionally ignored in Base version
        # PriorityPolicy_Pro will override this method and apply Pro logic

        return final_priority

    async def run_aging_worker(self, db_session: AsyncSession):
        logger.info("AgingWorker started")

        while True:
            try:
                await asyncio.sleep(self.aging_interval_sec)

                now_ts = int(time.time())
                threshold_ts = now_ts - self.aging_threshold_sec

                # Update executions table
                executions_query = text("""
                    UPDATE executions
                    SET priority = MIN(priority + :boost, :cap)
                    WHERE status = 'PENDING'
                      AND enqueue_ts < :threshold
                      AND priority < :cap
                """)

                result_exec = await db_session.execute(
                    executions_query,
                    {
                        "boost": self.aging_boost,
                        "cap": self.aging_cap,
                        "threshold": threshold_ts
                    }
                )

                # Update inference_queue table
                queue_query = text("""
                    UPDATE inference_queue
                    SET priority = MIN(priority + :boost, :cap)
                    WHERE status = 'PENDING'
                      AND enqueue_ts < :threshold
                      AND priority < :cap
                """)

                result_queue = await db_session.execute(
                    queue_query,
                    {
                        "boost": self.aging_boost,
                        "cap": self.aging_cap,
                        "threshold": threshold_ts
                    }
                )

                await db_session.commit()

                boosted_exec = result_exec.rowcount
                boosted_queue = result_queue.rowcount

                if boosted_exec > 0 or boosted_queue > 0:
                    logger.info(
                        f"AgingWorker boosted priorities: "
                        f"executions={boosted_exec}, queue={boosted_queue}"
                    )

            except Exception as e:
                logger.error(f"AgingWorker failed during priority update: {e}")
                # Do NOT crash the worker - continue loop
                try:
                    await db_session.rollback()
                except Exception:
                    pass


# Singleton instance (initialized by main.py on startup)
_priority_policy_instance: Optional[PriorityPolicy_Base] = None


def get_priority_policy() -> PriorityPolicy_Base:
    if _priority_policy_instance is None:
        raise RuntimeError("PriorityPolicy not initialized. Call init_priority_policy() first.")
    return _priority_policy_instance


def init_priority_policy(settings: Dict[str, Any]) -> PriorityPolicy_Base:
    global _priority_policy_instance
    if _priority_policy_instance is None:
        _priority_policy_instance = PriorityPolicy_Base(settings)
        logger.info("PriorityPolicy singleton initialized")
    return _priority_policy_instance
