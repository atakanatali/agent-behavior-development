"""
Migration 003: Scoring and recycle pattern tables.

Creates tables for ABD scorecards and recycle pattern tracking.
"""
from orchestify.migrations.runner import Migration


class ScoringPatterns(Migration):
    version = 3
    description = "Scorecards, recycle patterns"

    def up(self, db):
        conn = db.conn

        # issue_scorecards: ABD evaluation scorecards
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issue_scorecards (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id            INTEGER NOT NULL,
                agent_id            TEXT    NOT NULL,
                scope_control       INTEGER DEFAULT 0,
                behavior_fidelity   INTEGER DEFAULT 0,
                evidence_orientation INTEGER DEFAULT 0,
                actionability       INTEGER DEFAULT 0,
                risk_awareness      INTEGER DEFAULT 0,
                total               INTEGER DEFAULT 0,
                interpretation      TEXT,
                created_at          TEXT    NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES issues(id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scorecards_issue "
            "ON issue_scorecards(issue_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scorecards_agent "
            "ON issue_scorecards(agent_id)"
        )

        # issue_recycle_patterns: pattern tracking (kept/reused/banned)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issue_recycle_patterns (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id        INTEGER NOT NULL,
                pattern_type    TEXT    NOT NULL,
                pattern_value   TEXT    NOT NULL,
                applied_by      TEXT,
                applied_at      TEXT    NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES issues(id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_recycle_issue "
            "ON issue_recycle_patterns(issue_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_recycle_type "
            "ON issue_recycle_patterns(pattern_type)"
        )

    def down(self, db):
        conn = db.conn
        conn.execute("DROP TABLE IF EXISTS issue_recycle_patterns")
        conn.execute("DROP TABLE IF EXISTS issue_scorecards")


migration = ScoringPatterns()
