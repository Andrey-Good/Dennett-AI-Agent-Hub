# apps/ai_core/ai_core/db/session.py
"""
Database session management for SQLAlchemy.

This module handles database connection lifecycle, session factory creation,
and provides utilities for database operations.
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration for database connections."""
    
    def __init__(self, database_url: str, echo: bool = False, pool_size: int = 10, 
                 max_overflow: int = 20):
        """
        Initialize database configuration.
        
        Args:
            database_url: SQLAlchemy database URL
            echo: Enable SQL query logging
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
        """
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize the database manager.
        
        Args:
            config: DatabaseConfig instance
        """
        self.config = config
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.scoped_session: Optional[scoped_session] = None
    
    def initialize(self) -> Engine:
        """
        Initialize the database engine and session factory.
        
        Returns:
            SQLAlchemy Engine instance
            
        Raises:
            RuntimeError: If engine is already initialized
        """
        if self.engine is not None:
            raise RuntimeError("Database engine is already initialized")
        
        logger.info(f"Initializing database with URL: {self.config.database_url}")
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.config.database_url,
            echo=self.config.echo,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            connect_args={"check_same_thread": False}  # SQLite specific
        )
        
        # Configure event listeners
        self._setup_event_listeners()
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        self.scoped_session = scoped_session(self.SessionLocal)
        
        logger.info("Database initialized successfully")
        return self.engine
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for database operations."""
        if self.engine is None:
            return
        
        # Log connection pool statistics
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(self.engine, "close")
        def receive_close(dbapi_conn, connection_record):
            logger.debug("Database connection closed")
    
    def create_session(self) -> Session:
        """
        Create a new database session.
        
        Returns:
            SQLAlchemy Session instance
            
        Raises:
            RuntimeError: If engine not initialized
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.SessionLocal()
    
    def get_scoped_session(self) -> Session:
        """
        Get the current scoped session (thread-local).
        
        Returns:
            Current scoped session
            
        Raises:
            RuntimeError: If scoped_session not initialized
        """
        if self.scoped_session is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.scoped_session()
    
    def create_tables(self, base) -> None:
        """
        Create all database tables from ORM models.
        
        Args:
            base: SQLAlchemy declarative base with all models
            
        Raises:
            RuntimeError: If engine not initialized
        """
        if self.engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        logger.info("Creating database tables...")
        base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self, base) -> None:
        """
        Drop all database tables (use with caution).
        
        Args:
            base: SQLAlchemy declarative base with all models
            
        Raises:
            RuntimeError: If engine not initialized
        """
        if self.engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        logger.warning("Dropping all database tables...")
        base.metadata.drop_all(bind=self.engine)
        logger.warning("Database tables dropped")
    
    def get_engine(self) -> Engine:
        """
        Get the database engine.
        
        Returns:
            SQLAlchemy Engine instance
            
        Raises:
            RuntimeError: If engine not initialized
        """
        if self.engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.engine
    
    def close(self) -> None:
        """Close the database connection pool."""
        if self.scoped_session:
            self.scoped_session.remove()
        
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
    
    def health_check(self) -> bool:
        """
        Check database health by executing a simple query.
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            if self.engine is None:
                return False
            
            with self.engine.connect() as connection:
                connection.execute("SELECT 1")
            
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def initialize_database(config: DatabaseConfig) -> DatabaseManager:
    """
    Initialize the global database manager.
    
    Args:
        config: DatabaseConfig instance
        
    Returns:
        Initialized DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is not None:
        raise RuntimeError("Database already initialized")
    
    _db_manager = DatabaseManager(config)
    _db_manager.initialize()
    
    return _db_manager


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    
    return _db_manager


def get_session() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI that provides a database session.
    
    Yields:
        SQLAlchemy Session instance
        
    Usage:
        @app.get("/agents")
        def list_agents(session: Session = Depends(get_session)):
            return session.query(Agent).all()
    """
    db = get_database_manager()
    session = db.create_session()
    
    try:
        yield session
    finally:
        session.close()


def get_db() -> Optional[DatabaseManager]:
    """
    Get database manager for manual session creation.
    
    Returns:
        DatabaseManager instance or None if not initialized
    """
    return _db_manager
