# apps/ai_core/ai_core/db/migrations/add_trigger_instances.py
"""
Database migration: Add trigger_instances table for TriggerManager.

This script adds:
- trigger_instances table for storing trigger configurations and state
- Required indexes for efficient queries

Run this ONCE to migrate existing databases.
"""

from sqlalchemy import text
from apps.ai_core.ai_core.db.session import get_database_manager
import logging

logger = logging.getLogger(__name__)


def migrate_add_trigger_instances():
    """Add trigger_instances table if it doesn't exist."""
    db_manager = get_database_manager()
    engine = db_manager.get_engine()

    with engine.connect() as conn:
        try:
            # Check if trigger_instances table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trigger_instances'"
            ))
            if result.fetchone() is None:
                _create_trigger_instances_table(conn)
            else:
                logger.info("trigger_instances table already exists, skipping")

            conn.commit()
            logger.info("Trigger instances migration completed successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise


def _create_trigger_instances_table(conn):
    """Create trigger_instances table."""
    logger.info("Creating trigger_instances table...")

    conn.execute(text("""
        CREATE TABLE trigger_instances (
            trigger_instance_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            trigger_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ENABLED',
            config_json TEXT NOT NULL,
            config_hash TEXT NOT NULL,
            error_message TEXT,
            error_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
            CHECK (status IN ('ENABLED', 'DISABLED', 'FAILED'))
        )
    """))

    # Create indexes for efficient queries
    conn.execute(text("""
        CREATE INDEX idx_trigger_agent_id
        ON trigger_instances(agent_id)
    """))

    conn.execute(text("""
        CREATE INDEX idx_trigger_status
        ON trigger_instances(status)
    """))

    conn.execute(text("""
        CREATE INDEX idx_trigger_agent_status
        ON trigger_instances(agent_id, status)
    """))

    conn.execute(text("""
        CREATE INDEX idx_trigger_id
        ON trigger_instances(trigger_id)
    """))

    conn.execute(text("""
        CREATE INDEX idx_trigger_created_at
        ON trigger_instances(created_at)
    """))

    logger.info("Created trigger_instances table with indexes")


def run_migration():
    """Entry point for running the migration."""
    migrate_add_trigger_instances()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_add_trigger_instances()
