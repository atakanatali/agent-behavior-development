"""
Migration 001: Initial core schema.

Creates the foundational tables for sprint execution tracking:
sprints, epics, issues, and cycles.
"""
from orchestify.migrations.runner import Migration


class InitialSchema(Migration):
    version = 1
    description = "Core tables: sprints, epics, issues, cycles"

    def up(self, db):
        conn = db.conn

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sprints (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sprint_id   TEXT    NOT NULL UNIQUE,
                status      TEXT    NOT NULL DEFAULT 'created',
                prompt      TEXT,
                epic_id     TEXT,
                issues_total  INTEGER DEFAULT 0,
                issues_done   INTEGER DEFAULT 0,
                pid         INTEGER,
                error       TEXT,
                created_at  TEXT    NOT NULL,
                started_at  TEXT,
                paused_at   TEXT,
                completed_at TEXT,
                updated_at  TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sprints_status ON sprints(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sprints_created ON sprints(created_at)"
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS epics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                epic_id     TEXT    NOT NULL UNIQUE,
                sprint_id   TEXT,
                status      TEXT    NOT NULL DEFAULT 'pending',
                metadata    TEXT,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL,
                FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_epics_sprint ON epics(sprint_id)"
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_number    INTEGER NOT NULL,
                epic_id         TEXT    NOT NULL,
                sprint_id       TEXT,
                status          TEXT    NOT NULL DEFAULT 'pending',
                assigned_agent  TEXT,
                branch_name     TEXT,
                pr_number       INTEGER,
                review_cycles   INTEGER DEFAULT 0,
                qa_cycles       INTEGER DEFAULT 0,
                self_fix_attempts INTEGER DEFAULT 0,
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL,
                UNIQUE(issue_number, epic_id),
                FOREIGN KEY (epic_id)   REFERENCES epics(epic_id),
                FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_issues_epic ON issues(epic_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_issues_sprint ON issues(sprint_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)"
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cycles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id        INTEGER NOT NULL,
                cycle_number    INTEGER NOT NULL,
                agent_from      TEXT    NOT NULL,
                agent_to        TEXT    NOT NULL,
                action          TEXT    NOT NULL,
                result          TEXT,
                timestamp       TEXT    NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES issues(id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cycles_issue ON cycles(issue_id)"
        )

    def down(self, db):
        conn = db.conn
        conn.execute("DROP TABLE IF EXISTS cycles")
        conn.execute("DROP TABLE IF EXISTS issues")
        conn.execute("DROP TABLE IF EXISTS epics")
        conn.execute("DROP TABLE IF EXISTS sprints")


migration = InitialSchema()
