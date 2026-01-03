# dennett/core/priority.py
"""
PriorityPolicy: Assign priorities and run aging worker for anti-starvation.
"""

import asyncio
from datetime import datetime
from typing import Optional

class PriorityPolicy:
    """Priority scheduling with anti-starvation aging."""
    
    # Base priorities (коридоры источников)
    PRIORITY_CHAT = 90
    PRIORITY_MANUAL_RUN = 70
    PRIORITY_INTERNAL_NODE = 50
    PRIORITY_TRIGGER = 30

    # Anti-starvation parameters
    AGING_INTERVAL_SEC = 60
    AGING_THRESHOLD_SEC = 300
    AGING_BOOST = 10
    AGING_CAP_COMMUNITY = 65

    def __init__(self, db):
        self.db = db

    def assign_priority(
        self,
        source: str,
        parent_priority: Optional[int] = None,
        agent_config: Optional[dict] = None
    ) -> int:
        """
        Assign priority: max(base_priority_from_source, parent_priority)
        """
        base_map = {
            "CHAT": self.PRIORITY_CHAT,
            "MANUAL_RUN": self.PRIORITY_MANUAL_RUN,
            "INTERNAL_NODE": self.PRIORITY_INTERNAL_NODE,
            "TRIGGER": self.PRIORITY_TRIGGER,
        }
        base = base_map.get(source, self.PRIORITY_TRIGGER)
        
        if parent_priority is not None:
            return max(base, parent_priority)
        return base

    async def run_aging_worker(self):
        """
        Background worker: every 60s checks PENDING tasks > 300s old
        and increases priority by +10 (max 65 in Community).
        """
        print("🔄 AgingWorker started")
        
        while True:
            try:
                await asyncio.sleep(self.AGING_INTERVAL_SEC)
                
                now_ts = int(datetime.utcnow().timestamp())
                threshold_ts = now_ts - self.AGING_THRESHOLD_SEC

                # Update executions
                query = """
                    UPDATE executions
                    SET priority = MIN(priority + :boost, :cap)
                    WHERE status = 'PENDING'
                      AND enqueue_ts < :threshold
                """
                count1 = self.db.execute_update(query, {
                    "boost": self.AGING_BOOST,
                    "cap": self.AGING_CAP_COMMUNITY,
                    "threshold": threshold_ts,
                })

                # Update inference_queue
                query = """
                    UPDATE inference_queue
                    SET priority = MIN(priority + :boost, :cap)
                    WHERE status = 'PENDING'
                      AND enqueue_ts < :threshold
                """
                count2 = self.db.execute_update(query, {
                    "boost": self.AGING_BOOST,
                    "cap": self.AGING_CAP_COMMUNITY,
                    "threshold": threshold_ts,
                })
                
                if count1 > 0 or count2 > 0:
                    print(f"⬆️  AgingWorker: boosted {count1} executions, {count2} inference tasks")
                    
            except Exception as e:
                print(f"❌ AgingWorker error: {e}")
                await asyncio.sleep(1)
