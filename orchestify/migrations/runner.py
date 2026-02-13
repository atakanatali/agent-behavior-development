"""
Migration runner for orchestify database.

Discovers and executes pending migrations in order.
Supports forward-only migrations with rollback on failure.
"""
import importlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from orchestify.db.database import DatabaseManager

logger = logging.getLogger(__name__)


class Migration:
    """Base class for database migrations."""

    version: int = 0
    description: str = ""

    def up(self, db: DatabaseManager) -> None:
        """Apply the migration."""
        raise NotImplementedError

    def down(self, db: DatabaseManager) -> None:
        """Reverse the migration (best-effort)."""
        raise NotImplementedError


class MigrationRunner:
    """
    Discovers and runs database migrations.

    Migrations are Python modules in the versions/ directory that export
    a Migration subclass. They are executed in version order.
    """

    VERSIONS_PACKAGE = "orchestify.migrations.versions"

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        with self.db.transaction():
            self.db.conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    version     INTEGER NOT NULL UNIQUE,
                    description TEXT,
                    applied_at  TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'applied',
                    checksum    TEXT
                )
            """)

    def _discover_migrations(self) -> List[Migration]:
        """
        Import all migration modules from the versions package.

        Returns sorted list of Migration instances.
        """
        versions_dir = Path(__file__).parent / "versions"
        modules = sorted(versions_dir.glob("m[0-9]*.py"))

        migrations = []
        for mod_path in modules:
            mod_name = mod_path.stem
            full_name = f"{self.VERSIONS_PACKAGE}.{mod_name}"
            try:
                mod = importlib.import_module(full_name)
                if hasattr(mod, "migration"):
                    migrations.append(mod.migration)
                else:
                    logger.warning("Migration module %s has no 'migration' attribute", full_name)
            except Exception as e:
                logger.error("Failed to import migration %s: %s", full_name, e)
                raise

        # Sort by version number
        migrations.sort(key=lambda m: m.version)
        return migrations

    def get_applied_versions(self) -> List[int]:
        """Get list of already-applied migration versions."""
        rows = self.db.fetchall(
            "SELECT version FROM migrations WHERE status = 'applied' ORDER BY version"
        )
        return [row["version"] for row in rows]

    def get_pending(self) -> List[Migration]:
        """Get migrations that haven't been applied yet."""
        applied = set(self.get_applied_versions())
        all_migrations = self._discover_migrations()
        return [m for m in all_migrations if m.version not in applied]

    def run_pending(self) -> List[Tuple[int, str]]:
        """
        Run all pending migrations in order.

        Returns list of (version, description) tuples for applied migrations.
        """
        pending = self.get_pending()
        if not pending:
            logger.info("Database is up to date — no pending migrations.")
            return []

        applied = []
        for migration in pending:
            self._apply(migration)
            applied.append((migration.version, migration.description))

        logger.info("Applied %d migration(s).", len(applied))
        return applied

    def _apply(self, migration: Migration) -> None:
        """Apply a single migration within a transaction."""
        logger.info(
            "Applying migration %03d: %s",
            migration.version,
            migration.description,
        )
        try:
            with self.db.transaction():
                migration.up(self.db)
                self.db.conn.execute(
                    """
                    INSERT INTO migrations (version, description, applied_at, status)
                    VALUES (?, ?, ?, 'applied')
                    """,
                    (migration.version, migration.description, datetime.utcnow().isoformat()),
                )
            logger.info("Migration %03d applied successfully.", migration.version)
        except Exception as e:
            logger.error("Migration %03d failed: %s", migration.version, e)
            raise RuntimeError(
                f"Migration {migration.version:03d} failed: {e}"
            ) from e

    def rollback(self, target_version: int = 0) -> List[Tuple[int, str]]:
        """
        Rollback migrations down to (but not including) target_version.

        Returns list of (version, description) for rolled-back migrations.
        """
        applied = self.get_applied_versions()
        to_rollback = sorted(
            [v for v in applied if v > target_version],
            reverse=True,
        )

        if not to_rollback:
            logger.info("Nothing to rollback.")
            return []

        all_migrations = {m.version: m for m in self._discover_migrations()}
        rolled_back = []

        for version in to_rollback:
            migration = all_migrations.get(version)
            if migration is None:
                logger.warning("Migration %03d not found, skipping rollback.", version)
                continue
            self._rollback_one(migration)
            rolled_back.append((version, migration.description))

        return rolled_back

    def _rollback_one(self, migration: Migration) -> None:
        """Rollback a single migration."""
        logger.info(
            "Rolling back migration %03d: %s",
            migration.version,
            migration.description,
        )
        try:
            with self.db.transaction():
                migration.down(self.db)
                self.db.conn.execute(
                    "DELETE FROM migrations WHERE version = ?",
                    (migration.version,),
                )
            logger.info("Migration %03d rolled back.", migration.version)
        except Exception as e:
            logger.error("Rollback of %03d failed: %s", migration.version, e)
            raise

    def status(self) -> List[dict]:
        """
        Get status of all known migrations.

        Returns list of dicts with version, description, status, applied_at.
        """
        applied_map = {}
        rows = self.db.fetchall(
            "SELECT version, description, applied_at, status FROM migrations ORDER BY version"
        )
        for row in rows:
            applied_map[row["version"]] = {
                "applied_at": row["applied_at"],
                "status": row["status"],
            }

        all_migrations = self._discover_migrations()
        result = []
        for m in all_migrations:
            info = applied_map.get(m.version, {})
            result.append({
                "version": m.version,
                "description": m.description,
                "status": info.get("status", "pending"),
                "applied_at": info.get("applied_at"),
            })
        return result
