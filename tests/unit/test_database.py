"""Tests for orchestify.db.database — DatabaseManager and helpers."""
import sqlite3
import threading
from pathlib import Path

import pytest

from orchestify.db.database import DatabaseManager, get_db, reset_db, get_db_path


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def db(db_path):
    """Create a DatabaseManager instance."""
    return DatabaseManager(db_path)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level singleton between tests."""
    yield
    reset_db()


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    def test_creates_parent_dirs(self, tmp_path):
        """Should create parent directories if they don't exist."""
        db_path = tmp_path / "deep" / "nested" / "test.db"
        db = DatabaseManager(db_path)
        assert db_path.parent.exists()

    def test_creates_database_file(self, db):
        """Should create the database file on first access."""
        db.execute("SELECT 1")
        assert db.db_path.exists()

    def test_wal_mode(self, db):
        """Should enable WAL journal mode."""
        result = db.fetchval("PRAGMA journal_mode")
        assert result.lower() == "wal"

    def test_foreign_keys_enabled(self, db):
        """Should enable foreign keys."""
        result = db.fetchval("PRAGMA foreign_keys")
        assert result == 1

    def test_busy_timeout(self, db):
        """Should set busy timeout."""
        result = db.fetchval("PRAGMA busy_timeout")
        assert result == 5000

    def test_execute(self, db):
        """Should execute SQL statements."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES (?)", ("hello",))
        row = db.fetchone("SELECT name FROM test WHERE id = 1")
        assert row["name"] == "hello"

    def test_fetchone_returns_none(self, db):
        """Should return None when no rows match."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        result = db.fetchone("SELECT * FROM test WHERE id = 999")
        assert result is None

    def test_fetchall(self, db):
        """Should fetch all matching rows."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES ('a')")
        db.execute("INSERT INTO test (name) VALUES ('b')")
        rows = db.fetchall("SELECT name FROM test ORDER BY name")
        assert len(rows) == 2
        assert rows[0]["name"] == "a"
        assert rows[1]["name"] == "b"

    def test_fetchval(self, db):
        """Should fetch a single value."""
        result = db.fetchval("SELECT 42")
        assert result == 42

    def test_fetchval_returns_none(self, db):
        """Should return None for empty result."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        result = db.fetchval("SELECT id FROM test WHERE id = 999")
        assert result is None

    def test_transaction_commit(self, db):
        """Should commit changes in a transaction."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        with db.transaction():
            db.conn.execute("INSERT INTO test (val) VALUES ('committed')")
        row = db.fetchone("SELECT val FROM test WHERE id = 1")
        assert row["val"] == "committed"

    def test_transaction_rollback(self, db):
        """Should rollback on exception."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        try:
            with db.transaction():
                db.conn.execute("INSERT INTO test (val) VALUES ('rollback')")
                raise ValueError("test error")
        except ValueError:
            pass
        row = db.fetchone("SELECT val FROM test WHERE id = 1")
        assert row is None

    def test_table_exists(self, db):
        """Should check if table exists."""
        assert not db.table_exists("test")
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        assert db.table_exists("test")

    def test_close(self, db):
        """Should close connection without error."""
        db.execute("SELECT 1")
        db.close()
        # Should be able to reconnect
        db.execute("SELECT 1")

    def test_row_factory(self, db):
        """Should return Row objects with column access."""
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES ('test')")
        row = db.fetchone("SELECT * FROM test")
        assert row["id"] == 1
        assert row["name"] == "test"


class TestGetDb:
    """Tests for the singleton get_db function."""

    def test_requires_path_on_first_call(self):
        """Should raise error if no path provided on first call."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_db()

    def test_returns_same_instance(self, db_path):
        """Should return the same instance on subsequent calls."""
        db1 = get_db(db_path)
        db2 = get_db()
        assert db1 is db2

    def test_reset_allows_reinitialization(self, db_path, tmp_path):
        """Should allow re-initialization after reset."""
        db1 = get_db(db_path)
        reset_db()
        new_path = tmp_path / "new.db"
        db2 = get_db(new_path)
        assert db1 is not db2


class TestGetDbPath:
    """Tests for get_db_path helper."""

    def test_returns_global_path(self, tmp_path, monkeypatch):
        """Should return ~/.orchestify/data/orchestify.db (global home)."""
        monkeypatch.setenv("ORCHESTIFY_HOME", str(tmp_path / ".orchestify"))
        result = get_db_path()
        expected = tmp_path / ".orchestify" / "data" / "orchestify.db"
        assert result == expected

    def test_ignores_repo_root_param(self, tmp_path, monkeypatch):
        """repo_root param is ignored — DB is always in global home."""
        monkeypatch.setenv("ORCHESTIFY_HOME", str(tmp_path / ".orchestify"))
        result = get_db_path(tmp_path / "some-repo")
        expected = tmp_path / ".orchestify" / "data" / "orchestify.db"
        assert result == expected
