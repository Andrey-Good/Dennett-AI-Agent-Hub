# dennett/core/db.py
"""
DatabaseManager: Управление SQLite с WAL, PRAGMA, и thread-local connections.
"""

import sqlite3
import threading
from typing import Optional, Dict, Any
import json
from datetime import datetime

class DatabaseManager:
    """Thread-safe SQLite manager with WAL support."""
    
    def __init__(self, db_path: str = "storage.db"):
        self.db_path = db_path
        self.local = threading.local()
        self._ensure_schema()
        print(f"✓ DatabaseManager initialized: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create thread-local SQLite connection."""
        if not hasattr(self.local, "conn"):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
            self._apply_pragmas(self.local.conn)
        return self.local.conn

    def _apply_pragmas(self, conn: sqlite3.Connection):
        """Apply PRAGMA settings for WAL, concurrency, and performance."""
        pragmas = [
            "PRAGMA journal_mode=WAL;",
            "PRAGMA busy_timeout=5000;",
            "PRAGMA wal_autocheckpoint=1000;",
            "PRAGMA synchronous=NORMAL;",
        ]
        for pragma in pragmas:
            conn.execute(pragma)
        conn.commit()

    def _ensure_schema(self):
        """Create tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                execution_id        TEXT PRIMARY KEY,
                agent_id            TEXT NOT NULL,
                status              TEXT NOT NULL,
                parent_execution_id TEXT,
                final_result        TEXT,
                base_priority       INTEGER NOT NULL,
                priority            INTEGER NOT NULL,
                enqueue_ts          INTEGER NOT NULL,
                boost_expires_at    INTEGER,
                lease_id            TEXT,
                lease_expires_at    INTEGER,
                created_at          INTEGER NOT NULL DEFAULT (CAST(strftime('%s', 'now') AS INTEGER)),
                started_at          INTEGER,
                completed_at        INTEGER,
                error_log           TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_executions_queue
            ON executions (status, priority DESC, enqueue_ts ASC)
        """)

        # inference_queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inference_queue (
                task_id            TEXT PRIMARY KEY,
                model_id           TEXT NOT NULL,
                status             TEXT NOT NULL,
                prompt             TEXT NOT NULL,
                parameters         TEXT NOT NULL,
                result             TEXT,
                base_priority      INTEGER NOT NULL,
                priority           INTEGER NOT NULL,
                enqueue_ts         INTEGER NOT NULL,
                boost_expires_at   INTEGER,
                lease_id           TEXT,
                lease_expires_at   INTEGER,
                created_at         INTEGER NOT NULL DEFAULT (CAST(strftime('%s', 'now') AS INTEGER)),
                started_at         INTEGER,
                completed_at       INTEGER,
                tokens_per_second  REAL,
                error_log          TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_inference_queue
            ON inference_queue (status, priority DESC, enqueue_ts ASC)
        """)

        # node_events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_events (
                event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id        TEXT NOT NULL,
                node_id             TEXT NOT NULL,
                status              TEXT NOT NULL,
                intermediate_output TEXT,
                started_at          INTEGER,
                completed_at        INTEGER,
                error_log           TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_node_events_exec
            ON node_events (execution_id, event_id)
        """)

        conn.commit()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute SELECT query, return first row as dict."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        row = cursor.fetchone()
        return dict(row) if row else None

    def execute_update(self, query: str, params: Optional[Dict] = None) -> int:
        """Execute INSERT/UPDATE/DELETE, return row count."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        conn.commit()
        return cursor.rowcount

    def execute_returning(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute statement with RETURNING, return first row as dict."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        conn.commit()
        row = cursor.fetchone()
        return dict(row) if row else None

    def transaction(self):
        """Context manager for transactions."""
        class _Transaction:
            def __init__(self, db):
                self.db = db
            def __enter__(self):
                self.db._get_connection().execute("BEGIN")
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.db._get_connection().rollback()
                else:
                    self.db._get_connection().commit()
        return _Transaction(self)
