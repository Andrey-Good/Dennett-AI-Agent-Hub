# apps/ai_core/ai_core/db/init_db.py
"""
Database initialization script for AI Core.

This module handles database creation, schema initialization, and migrations.
Run this script once during application setup to create the database and tables.
"""

import os
import sys
from pathlib import Path
import logging
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url(db_dir: Optional[str] = None) -> str:
    """
    Get the SQLite database URL.
    
    Args:
        db_dir: Optional directory path for database file. 
                If None, uses default from config.
    
    Returns:
        SQLAlchemy database URL
    """
    if db_dir is None:
        # Use default AppData directory from config
        from apps.ai_core.ai_core.config.settings import APP_DATA_DIR
        db_dir = str(APP_DATA_DIR / "db")
    
    # Ensure directory exists
    db_path = Path(db_dir)
    db_path.mkdir(exist_ok=True, parents=True)
    
    # SQLite database file path
    db_file = db_path / "storage.db"
    
    # Return SQLAlchemy URL (SQLite)
    return f"sqlite:///{db_file}"


def init_database(db_url: Optional[str] = None, drop_existing: bool = False) -> bool:
    """
    Initialize the database with all required tables.
    
    Args:
        db_url: Optional SQLAlchemy database URL. If None, uses default.
        drop_existing: If True, drop existing tables before creation (be careful!)
    
    Returns:
        True if initialization successful, False otherwise
    
    Raises:
        Exception: If database initialization fails
    """
    try:
        logger.info("Starting database initialization...")
        
        # Import database components
        from apps.ai_core.ai_core.db.session import DatabaseConfig, DatabaseManager
        from apps.ai_core.ai_core.db.orm_models import Base
        
        # Get database URL
        if db_url is None:
            db_url = get_database_url()
        
        logger.info(f"Using database URL: {db_url}")
        
        # Create database configuration
        config = DatabaseConfig(
            database_url=db_url,
            echo=False,  # Set to True for SQL debugging
            pool_size=5,
            max_overflow=10
        )
        
        # Initialize database manager
        db_manager = DatabaseManager(config)
        engine = db_manager.initialize()
        
        # Drop tables if requested
        if drop_existing:
            logger.warning("Dropping existing tables...")
            db_manager.drop_tables(Base)
            logger.info("Tables dropped")
        
        # Create all tables from ORM models
        db_manager.create_tables(Base)
        
        # Perform health check
        if db_manager.health_check():
            logger.info("✅ Database initialized successfully")
            return True
        else:
            logger.error("❌ Database health check failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise


def seed_database() -> None:
    """
    Seed database with sample data for testing.
    
    This is optional and useful for development/testing.
    """
    try:
        logger.info("Seeding database with sample data...")
        
        from apps.ai_core.ai_core.db.session import get_database_manager
        from apps.ai_core.ai_core.db.repositories import (
            AgentRepository, AgentRunRepository, AgentTestCaseRepository
        )
        
        db = get_database_manager()
        session = db.create_session()
        
        try:
            # Create sample agents
            agent_repo = AgentRepository(session)
            
            agent1 = agent_repo.create(
                name="News Aggregator",
                description="Aggregates and summarizes news from multiple sources",
                tags=["news", "aggregation", "llm"]
            )
            logger.info(f"Created sample agent: {agent1.name} ({agent1.id})")
            
            agent2 = agent_repo.create(
                name="API Integration Bot",
                description="Integrates with various APIs and processes responses",
                tags=["api", "integration", "automation"]
            )
            logger.info(f"Created sample agent: {agent2.name} ({agent2.id})")
            
            # Create sample runs
            run_repo = AgentRunRepository(session)
            
            run1 = run_repo.create(
                agent_id=agent1.id,
                trigger_type="schedule",
                status="completed"
            )
            run_repo.update_status(run1.run_id, "completed")
            logger.info(f"Created sample run: {run1.run_id}")
            
            # Create sample test cases
            test_repo = AgentTestCaseRepository(session)
            
            test1 = test_repo.create(
                agent_id=agent1.id,
                node_id="node_001",
                name="Test empty input",
                initial_state={"input": "", "expected_output": "Error message"}
            )
            logger.info(f"Created sample test case: {test1.name} ({test1.case_id})")
            
            logger.info("✅ Database seeding completed")
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Database seeding failed: {e}", exc_info=True)
        raise


def verify_database() -> bool:
    """
    Verify database integrity and list basic statistics.
    
    Returns:
        True if database is valid, False otherwise
    """
    try:
        logger.info("Verifying database...")
        
        from apps.ai_core.ai_core.db.session import get_database_manager
        from apps.ai_core.ai_core.db.repositories import (
            AgentRepository, AgentRunRepository, AgentTestCaseRepository
        )
        
        db = get_database_manager()
        session = db.create_session()
        
        try:
            agent_repo = AgentRepository(session)
            run_repo = AgentRunRepository(session)
            test_repo = AgentTestCaseRepository(session)
            
            agent_count = agent_repo.count_all()
            run_count = session.query(AgentRunRepository).count() if run_repo else 0
            
            logger.info(f"📊 Database Statistics:")
            logger.info(f"   Agents: {agent_count}")
            logger.info(f"   Agent Runs: {run_count}")
            
            logger.info("✅ Database verification passed")
            return True
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}", exc_info=True)
        return False


def main():
    """
    Main entry point for database initialization.
    
    Supports command line arguments:
        python init_db.py               # Initialize database
        python init_db.py --seed        # Initialize and seed with sample data
        python init_db.py --drop-seed   # Drop existing and seed new data
        python init_db.py --verify      # Verify database integrity
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Database initialization utility')
    parser.add_argument('--seed', action='store_true', 
                        help='Seed database with sample data')
    parser.add_argument('--drop-seed', action='store_true',
                        help='Drop existing tables and seed with sample data')
    parser.add_argument('--verify', action='store_true',
                        help='Verify database integrity')
    parser.add_argument('--db-url', type=str, default=None,
                        help='Custom database URL')
    
    args = parser.parse_args()
    
    try:
        # Initialize database
        drop_existing = args.drop_seed
        init_database(db_url=args.db_url, drop_existing=drop_existing)
        
        # Seed if requested
        if args.seed or args.drop_seed:
            seed_database()
        
        # Verify if requested or after initialization
        if args.verify or args.seed or args.drop_seed:
            verify_database()
        
        logger.info("\n✅ All operations completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"\n❌ Operation failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
