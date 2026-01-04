# dennett/core/recovery.py
"""
StartupRecovery: Restore RUNNING/CANCEL_REQUESTED tasks back to PENDING on startup.
"""

class StartupRecovery:
    """Recovery mechanism for crash situations."""
    
    @staticmethod
    def recover(db):
        """
        On startup: return RUNNING and CANCEL_REQUESTED tasks back to PENDING.
        This ensures no tasks are lost after process crash.
        """
        # Recover executions
        query = """
            UPDATE executions
            SET status = 'PENDING', lease_id = NULL, lease_expires_at = NULL
            WHERE status IN ('RUNNING', 'CANCEL_REQUESTED')
        """
        count1 = db.execute_update(query)

        # Recover inference_queue
        query = """
            UPDATE inference_queue
            SET status = 'PENDING', lease_id = NULL, lease_expires_at = NULL
            WHERE status IN ('RUNNING', 'CANCEL_REQUESTED')
        """
        count2 = db.execute_update(query)

        if count1 > 0 or count2 > 0:
            print(f"🔄 StartupRecovery: {count1} executions, {count2} inference tasks recovered")
