"""
Database migration: Add priority column to agent_runs table.

This script adds the priority column and index to existing database.
Run this ONCE to migrate existing databases.
"""

from sqlalchemy import text
import logging

try:
    from apps.ai_core.ai_core.db.session import get_database_manager
except ModuleNotFoundError:
    from ai_core.db.session import get_database_manager

logger = logging.getLogger(__name__)


def migrate_add_priority_column():
    """Add priority column to agent_runs table."""
    db_manager = get_database_manager()
    engine = db_manager.get_engine()

    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(agent_runs)"))
            columns = [row[1] for row in result]

            if 'priority' in columns:
                logger.info("Priority column already exists, skipping migration")
                return

            # Add priority column with default value
            logger.info("Adding priority column to agent_runs table...")
            conn.execute(text("""
                ALTER TABLE agent_runs 
                ADD COLUMN priority INTEGER NOT NULL DEFAULT 30
            """))

            # Create index for priority-based queries
            logger.info("Creating priority index...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agent_run_priority 
                ON agent_runs(status, priority)
            """))

            conn.commit()
            logger.info("? Migration completed successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"? Migration failed: {e}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_add_priority_column()
