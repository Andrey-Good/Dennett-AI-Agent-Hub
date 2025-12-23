"""
Database migration: Add versioning and drafts support for agents (v5.0).

This script adds:
- version, is_active, deletion_status, file_path columns to agents table
- agent_drafts table for draft/branch management
- Required indexes

Run this ONCE to migrate existing databases.
"""

from sqlalchemy import text
from apps.ai_core.ai_core.db.session import get_database_manager
import logging

logger = logging.getLogger(__name__)


def migrate_add_agent_versioning():
    """Add versioning columns to agents table and create agent_drafts table."""
    db_manager = get_database_manager()
    engine = db_manager.get_engine()

    with engine.connect() as conn:
        try:
            # Check if migration already applied by checking for version column
            result = conn.execute(text("PRAGMA table_info(agents)"))
            columns = [row[1] for row in result]

            if 'version' in columns:
                logger.info("Agent versioning columns already exist, skipping migration")
            else:
                _add_agent_columns(conn, columns)

            # Check if agent_drafts table exists
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_drafts'"
            ))
            if result.fetchone() is None:
                _create_drafts_table(conn)
            else:
                logger.info("agent_drafts table already exists, skipping")

            conn.commit()
            logger.info("Migration completed successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise


def _add_agent_columns(conn, existing_columns):
    """Add versioning columns to agents table."""
    logger.info("Adding versioning columns to agents table...")

    # Add version column
    if 'version' not in existing_columns:
        conn.execute(text("""
            ALTER TABLE agents
            ADD COLUMN version INTEGER NOT NULL DEFAULT 1
        """))
        logger.info("Added 'version' column")

    # Add is_active column
    if 'is_active' not in existing_columns:
        conn.execute(text("""
            ALTER TABLE agents
            ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0
        """))
        logger.info("Added 'is_active' column")

    # Add deletion_status column
    if 'deletion_status' not in existing_columns:
        conn.execute(text("""
            ALTER TABLE agents
            ADD COLUMN deletion_status TEXT NOT NULL DEFAULT 'NONE'
        """))
        logger.info("Added 'deletion_status' column")

    # Add file_path column
    if 'file_path' not in existing_columns:
        conn.execute(text("""
            ALTER TABLE agents
            ADD COLUMN file_path TEXT
        """))
        logger.info("Added 'file_path' column")

    # Create indexes
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_agent_deletion_status
        ON agents(deletion_status)
    """))
    logger.info("Created deletion_status index")


def _create_drafts_table(conn):
    """Create agent_drafts table."""
    logger.info("Creating agent_drafts table...")

    conn.execute(text("""
        CREATE TABLE agent_drafts (
            draft_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            base_version INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            his_execution_id TEXT,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
            CHECK (base_version >= 1)
        )
    """))

    # Create index for agent_id + updated_at queries
    conn.execute(text("""
        CREATE INDEX idx_draft_agent_updated
        ON agent_drafts(agent_id, updated_at DESC)
    """))

    logger.info("Created agent_drafts table with indexes")


def run_migration():
    """Entry point for running the migration."""
    migrate_add_agent_versioning()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_add_agent_versioning()
