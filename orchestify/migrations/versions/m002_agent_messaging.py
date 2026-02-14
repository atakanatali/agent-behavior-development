"""
Migration 002: Agent messaging and logging tables.

Creates tables for agent console output, inter-agent communication,
and structured event logging.
"""
from orchestify.migrations.runner import Migration


class AgentMessaging(Migration):
    version = 2
    description = "Agent messaging and logging: agent_messages, agent_logs"

    def up(self, db):
        conn = db.conn

        # agent_messages: console output + inter-agent messaging + streaming
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                sprint_id       TEXT    NOT NULL,
                agent_id        TEXT    NOT NULL,
                message_type    TEXT    NOT NULL,
                content         TEXT    NOT NULL,
                epic_id         TEXT,
                issue_id        INTEGER,
                level           TEXT    DEFAULT 'INFO',
                related_agent   TEXT,
                metadata        TEXT,
                timestamp       TEXT    NOT NULL,
                FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
            )
        """)
        # Primary query pattern: tail by sprint+agent, ordered by timestamp
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_sprint_agent "
            "ON agent_messages(sprint_id, agent_id, timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp "
            "ON agent_messages(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_type "
            "ON agent_messages(message_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_issue "
            "ON agent_messages(issue_id)"
        )

        # agent_logs: structured event logs (replaces JSONL files)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sprint_id   TEXT    NOT NULL,
                agent_id    TEXT    NOT NULL,
                event       TEXT    NOT NULL,
                level       TEXT    NOT NULL DEFAULT 'INFO',
                data        TEXT,
                timestamp   TEXT    NOT NULL,
                FOREIGN KEY (sprint_id) REFERENCES sprints(sprint_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_sprint_agent "
            "ON agent_logs(sprint_id, agent_id, timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_event "
            "ON agent_logs(event)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_level "
            "ON agent_logs(level)"
        )

    def down(self, db):
        conn = db.conn
        conn.execute("DROP TABLE IF EXISTS agent_logs")
        conn.execute("DROP TABLE IF EXISTS agent_messages")


migration = AgentMessaging()
