"""
SQLite database manager for orchestify.

Provides connection management with WAL mode, proper pragmas,
and concurrent reader support.
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Default pragmas for performance and concurrency
DEFAULT_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "cache_size": -64000,       # 64MB
    "temp_store": "MEMORY",
    "mmap_size": 30000000,      # 30MB
    "page_size": 4096,
    "busy_timeout": 5000,       # 5 seconds
    "foreign_keys": "ON",
}


class DatabaseManager:
    """
    Thread-safe SQLite database manager.

    Supports concurrent readers (via WAL) and serialized writes.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.RLock()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            # Apply pragmas
            for pragma, value in DEFAULT_PRAGMAS.items():
                conn.execute(f"PRAGMA {pragma} = {value}")
            self._local.conn = conn
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        """Current thread's connection."""
        return self._get_connection()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement."""
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement with multiple parameter sets."""
        return self.conn.executemany(sql, params_list)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute and fetch one row."""
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute and fetch all rows."""
        return self.conn.execute(sql, params).fetchall()

    def fetchval(self, sql: str, params: tuple = ()) -> Any:
        """Execute and fetch a single value."""
        row = self.fetchone(sql, params)
        return row[0] if row else None

    @contextmanager
    def transaction(self):
        """Context manager for write transactions with locking."""
        with self._write_lock:
            conn = self.conn
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def close(self):
        """Close the current thread's connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        row = self.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return row is not None

    def get_schema_version(self) -> int:
        """Get current schema version from migrations table."""
        if not self.table_exists("migrations"):
            return 0
        row = self.fetchone(
            "SELECT MAX(version) FROM migrations WHERE status='applied'"
        )
        return row[0] if row and row[0] else 0


# Module-level singleton for convenience
_db_instance: Optional[DatabaseManager] = None
_db_lock = threading.Lock()


def get_db(db_path: Optional[Path] = None) -> DatabaseManager:
    """
    Get or create the database manager singleton.

    Args:
        db_path: Path to database file. Required on first call.

    Returns:
        DatabaseManager instance
    """
    global _db_instance
    with _db_lock:
        if _db_instance is None:
            if db_path is None:
                raise RuntimeError("Database not initialized. Call get_db(path) first.")
            _db_instance = DatabaseManager(db_path)
        return _db_instance


def reset_db():
    """Reset the singleton (for testing)."""
    global _db_instance
    with _db_lock:
        if _db_instance:
            _db_instance.close()
        _db_instance = None


def get_db_path(repo_root: Path = None) -> Path:
    """
    Get the standard database path.

    The database lives in the global ~/.orchestify/data/ directory,
    NOT in the project root.

    Args:
        repo_root: Ignored (kept for backward compatibility). DB is always global.
    """
    from orchestify.core.global_config import get_orchestify_home
    return get_orchestify_home() / "data" / "orchestify.db"
