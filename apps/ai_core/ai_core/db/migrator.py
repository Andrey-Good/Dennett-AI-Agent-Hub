# apps/ai_core/ai_core/db/migrator.py
"""
Database Migrator module for AI Core.

This module runs ONCE on first startup to initialize the database structure.
It creates all required tables, sets up SQLite PRAGMA settings, and populates
default settings.
"""

import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """
    Handles database initialization and schema migrations.
    
    This class is responsible for:
    - Checking if database is already initialized (via PRAGMA user_version)
    - Setting up SQLite PRAGMA settings for optimal performance
    - Creating all required tables from the blueprint
    - Populating default settings
    - Setting user_version to mark initialization complete
    """
    
    # Default settings dictionary
    DEFAULT_SETTINGS = {
        'HEAVY_ASSET_PATH': '~/DennettData',
        'API_HOST': '127.0.0.1',
        'API_PORT': '13337',
        'AGING_INTERVAL_SEC': '60',
        'AGING_THRESHOLD_SEC': '300',
        'AGING_BOOST': '10',
        'AGING_CAP_COMMUNITY': '65',
        'MAX_CONCURRENT_DOWNLOADS': '3',
        'DOWNLOAD_CHUNK_SIZE': '8192',
        'DOWNLOAD_TIMEOUT': '300',
        'LOG_LEVEL': 'INFO',
        'ENABLE_CORS': 'true',
        'CLEANUP_INTERVAL_HOURS': '24',
        'MAX_SEARCH_RESULTS': '100',
    }
    
    def __init__(self, engine: Engine):
        """
        Initialize the DatabaseMigrator.
        
        Args:
            engine: SQLAlchemy Engine instance
        """
        self.engine = engine
    
    def needs_initialization(self) -> bool:
        """
        Check if database needs initialization by checking user_version.
        
        Returns:
            True if database is uninitialized (user_version == 0), False otherwise
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("PRAGMA user_version"))
            version = result.scalar()
            logger.info(f"Current database user_version: {version}")
            return version == 0
    
    def set_user_version(self, version: int) -> None:
        """
        Set the database user_version.
        
        Args:
            version: Version number to set
        """
        with self.engine.connect() as conn:
            conn.execute(text(f"PRAGMA user_version = {version}"))
            conn.commit()
            logger.info(f"Set database user_version to {version}")
    
    def setup_pragma_settings(self) -> None:
        """
        Set up SQLite PRAGMA settings for optimal performance.
        
        Sets:
        - journal_mode=WAL: Write-Ahead Logging for better concurrency
        - synchronous=NORMAL: Balance between safety and performance
        - busy_timeout=5000: Wait up to 5 seconds if database is locked
        """
        logger.info("Setting up SQLite PRAGMA settings...")
        
        with self.engine.connect() as conn:
            # Enable WAL mode for better concurrent access
            result = conn.execute(text("PRAGMA journal_mode=WAL"))
            logger.info(f"✅ PRAGMA journal_mode=WAL: {result.scalar()}")
            
            # Set synchronous mode to NORMAL for performance
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            logger.info("✅ PRAGMA synchronous=NORMAL")
            
            # Set busy timeout to 5 seconds
            conn.execute(text("PRAGMA busy_timeout=5000"))
            logger.info("✅ PRAGMA busy_timeout=5000")
            
            conn.commit()
    
    def create_settings_table(self) -> None:
        """
        Create the settings table for storing key-value configuration.
        """
        logger.info("Creating settings table...")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
            logger.info("✅ Settings table created")
    
    def populate_default_settings(self) -> None:
        """
        Populate the settings table with default values.
        """
        logger.info("Populating default settings...")
        
        with self.engine.connect() as conn:
            for key, value in self.DEFAULT_SETTINGS.items():
                insert_sql = text(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (:key, :value)"
                )
                conn.execute(insert_sql, {"key": key, "value": value})
                logger.debug(f"  - {key}: {value}")
            
            conn.commit()
            logger.info(f"✅ Inserted {len(self.DEFAULT_SETTINGS)} default settings")
    
    def create_all_tables(self) -> None:
        """
        Create all application tables from ORM models.
        
        This imports the Base from orm_models and creates all defined tables.
        """
        logger.info("Creating application tables...")
        
        try:
            from apps.ai_core.ai_core.db.orm_models import Base
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ All application tables created")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
    
    def create_blueprint_tables(self) -> None:
        """
        Create additional tables from the Dennett blueprint.
        
        These tables may not be in ORM models yet but are required by the blueprint:
        - models: Stores AI model metadata
        - triggers: Stores trigger configurations
        - executions: Tracks execution history
        - inference_queue: Queue for inference requests
        - node_events: Stores workflow node events
        - rollup_watermark: Tracks data aggregation progress
        - agent_rollup_day/total: Daily and total agent statistics
        - model_rollup_day/total: Daily and total model statistics
        """
        logger.info("Creating blueprint-specific tables...")
        
        # SQL statements for blueprint tables
        blueprint_tables = [
            # Models table
            """
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_type TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Triggers table
            """
            CREATE TABLE IF NOT EXISTS triggers (
                trigger_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                config TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
            """,
            
            # Executions table
            """
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                run_id TEXT,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
            """,
            
            # Inference queue table
            """
            CREATE TABLE IF NOT EXISTS inference_queue (
                queue_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                request_data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE
            )
            """,
            
            # Node events table
            """
            CREATE TABLE IF NOT EXISTS node_events (
                event_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                run_id TEXT,
                node_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
            """,
            
            # Rollup watermark table
            """
            CREATE TABLE IF NOT EXISTS rollup_watermark (
                entity_type TEXT PRIMARY KEY,
                last_processed_timestamp TIMESTAMP NOT NULL
            )
            """,
            
            # Agent rollup day table
            """
            CREATE TABLE IF NOT EXISTS agent_rollup_day (
                agent_id TEXT NOT NULL,
                date TEXT NOT NULL,
                execution_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                total_duration_sec REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (agent_id, date),
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
            """,
            
            # Agent rollup total table
            """
            CREATE TABLE IF NOT EXISTS agent_rollup_total (
                agent_id TEXT PRIMARY KEY,
                execution_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                total_duration_sec REAL NOT NULL DEFAULT 0,
                last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
            """,
            
            # Model rollup day table
            """
            CREATE TABLE IF NOT EXISTS model_rollup_day (
                model_id TEXT NOT NULL,
                date TEXT NOT NULL,
                inference_count INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                total_duration_sec REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (model_id, date),
                FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE
            )
            """,
            
            # Model rollup total table
            """
            CREATE TABLE IF NOT EXISTS model_rollup_total (
                model_id TEXT PRIMARY KEY,
                inference_count INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                total_duration_sec REAL NOT NULL DEFAULT 0,
                last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE
            )
            """,
        ]
        
        with self.engine.connect() as conn:
            for i, table_sql in enumerate(blueprint_tables, 1):
                try:
                    conn.execute(text(table_sql))
                    logger.debug(f"  - Created table {i}/{len(blueprint_tables)}")
                except Exception as e:
                    logger.error(f"  - Failed to create table {i}: {e}")
                    raise
            
            conn.commit()
            logger.info(f"✅ Created {len(blueprint_tables)} blueprint tables")
    
    def migrate(self) -> None:
        """
        Run the full migration process.
        
        This is the main entry point for database initialization.
        Steps:
        1. Check if initialization is needed
        2. Set up PRAGMA settings
        3. Create all tables
        4. Create and populate settings table
        5. Set user_version to 1
        """
        logger.info("="*60)
        logger.info("Starting DatabaseMigrator...")
        logger.info("="*60)
        
        if not self.needs_initialization():
            logger.info("✅ Database already initialized. Nothing to do.")
            return
        
        logger.info("🔧 First-time initialization detected. Building database...")
        
        try:
            # Step 1: Setup PRAGMA settings
            self.setup_pragma_settings()
            
            # Step 2: Create ORM tables
            self.create_all_tables()
            
            # Step 3: Create blueprint-specific tables
            self.create_blueprint_tables()
            
            # Step 4: Create settings table
            self.create_settings_table()
            
            # Step 5: Populate default settings
            self.populate_default_settings()
            
            # Step 6: Mark initialization complete
            self.set_user_version(1)
            
            logger.info("="*60)
            logger.info("✅ Database initialization COMPLETE!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error("="*60)
            logger.error(f"❌ Database initialization FAILED: {e}")
            logger.error("="*60)
            raise


def run_migration(engine: Engine) -> None:
    """
    Convenience function to run database migration.

    Args:
        engine: SQLAlchemy Engine instance
    """
    migrator = DatabaseMigrator(engine)
    migrator.migrate()


def run_incremental_migrations(engine: Engine) -> None:
    """
    Run incremental migrations for existing databases.

    This function runs migrations that add new columns or tables
    to already-initialized databases.

    Args:
        engine: SQLAlchemy Engine instance
    """
    logger.info("Running incremental migrations...")

    try:
        # Import and run agent versioning migration
        from apps.ai_core.ai_core.db.migrations.add_agent_versioning import (
            migrate_add_agent_versioning
        )
        migrate_add_agent_versioning()
        logger.info("Incremental migrations completed")

    except Exception as e:
        logger.error(f"Incremental migration failed: {e}")
        raise
