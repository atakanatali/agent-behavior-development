"""Tests for orchestify.migrations — MigrationRunner and version modules."""
from pathlib import Path

import pytest

from orchestify.db.database import DatabaseManager
from orchestify.migrations.runner import MigrationRunner


@pytest.fixture
def db(tmp_path):
    """Create a DatabaseManager with a temporary database."""
    db_path = tmp_path / "test_migrations.db"
    return DatabaseManager(db_path)


@pytest.fixture
def runner(db):
    """Create a MigrationRunner instance."""
    return MigrationRunner(db)


class TestMigrationRunner:
    """Tests for MigrationRunner."""

    def test_creates_migrations_table(self, runner, db):
        """Should create the migrations tracking table."""
        assert db.table_exists("migrations")

    def test_discovers_migrations(self, runner):
        """Should discover all migration modules."""
        migrations = runner._discover_migrations()
        assert len(migrations) == 3
        assert migrations[0].version == 1
        assert migrations[1].version == 2
        assert migrations[2].version == 3

    def test_get_applied_versions_empty(self, runner):
        """Should return empty list when no migrations applied."""
        assert runner.get_applied_versions() == []

    def test_get_pending_all(self, runner):
        """Should return all migrations as pending initially."""
        pending = runner.get_pending()
        assert len(pending) == 3

    def test_run_pending(self, runner, db):
        """Should apply all pending migrations."""
        applied = runner.run_pending()
        assert len(applied) == 3
        assert applied[0] == (1, "Core tables: sprints, epics, issues, cycles")
        assert applied[1] == (2, "Agent messaging and logging: agent_messages, agent_logs")
        assert applied[2] == (3, "Scorecards, recycle patterns")

    def test_run_pending_idempotent(self, runner):
        """Should be idempotent — no-op when all applied."""
        runner.run_pending()
        applied = runner.run_pending()
        assert len(applied) == 0

    def test_creates_all_tables(self, runner, db):
        """Should create all 9 tables after running all migrations."""
        runner.run_pending()

        expected_tables = [
            "migrations",
            "sprints", "epics", "issues", "cycles",
            "agent_messages", "agent_logs",
            "issue_scorecards", "issue_recycle_patterns",
        ]
        for table in expected_tables:
            assert db.table_exists(table), f"Table {table} should exist"

    def test_migration_status(self, runner):
        """Should report correct status for each migration."""
        # Before running
        status = runner.status()
        assert all(s["status"] == "pending" for s in status)

        # After running
        runner.run_pending()
        status = runner.status()
        assert all(s["status"] == "applied" for s in status)
        assert all(s["applied_at"] is not None for s in status)

    def test_applied_versions_tracked(self, runner):
        """Should track applied versions in migrations table."""
        runner.run_pending()
        versions = runner.get_applied_versions()
        assert versions == [1, 2, 3]

    def test_rollback(self, runner, db):
        """Should rollback migrations."""
        runner.run_pending()
        assert db.table_exists("issue_scorecards")

        rolled = runner.rollback(target_version=2)
        assert len(rolled) == 1
        assert rolled[0][0] == 3
        assert not db.table_exists("issue_scorecards")

    def test_rollback_multiple(self, runner, db):
        """Should rollback multiple migrations."""
        runner.run_pending()

        rolled = runner.rollback(target_version=0)
        assert len(rolled) == 3
        assert not db.table_exists("sprints")

    def test_schema_version(self, db, runner):
        """Should track schema version."""
        assert db.get_schema_version() == 0
        runner.run_pending()
        assert db.get_schema_version() == 3


class TestMigration001:
    """Tests for the initial schema migration."""

    def test_sprints_table_structure(self, runner, db):
        """Should create sprints table with correct columns."""
        runner.run_pending()
        db.execute(
            "INSERT INTO sprints (sprint_id, status, created_at, updated_at) "
            "VALUES ('test-1', 'created', '2025-01-01', '2025-01-01')"
        )
        row = db.fetchone("SELECT * FROM sprints WHERE sprint_id = 'test-1'")
        assert row is not None
        assert row["status"] == "created"

    def test_issues_unique_constraint(self, runner, db):
        """Should enforce unique issue_number + epic_id."""
        runner.run_pending()
        db.execute(
            "INSERT INTO epics (epic_id, created_at, updated_at) "
            "VALUES ('epic-1', '2025-01-01', '2025-01-01')"
        )
        db.execute(
            "INSERT INTO issues (issue_number, epic_id, created_at, updated_at) "
            "VALUES (1, 'epic-1', '2025-01-01', '2025-01-01')"
        )
        with pytest.raises(Exception):
            db.execute(
                "INSERT INTO issues (issue_number, epic_id, created_at, updated_at) "
                "VALUES (1, 'epic-1', '2025-01-01', '2025-01-01')"
            )
