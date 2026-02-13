"""
Repository classes for orchestify database.

Each repository provides CRUD operations for its corresponding table(s).
All write operations use transactions for consistency.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from orchestify.db.database import DatabaseManager
from orchestify.db.models import (
    AgentLogRow,
    AgentMessageRow,
    CycleRow,
    EpicRow,
    IssueRow,
    RecyclePatternRow,
    ScorecardRow,
    SprintRow,
)


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row_to_dict(row) -> Optional[Dict[str, Any]]:
    """Convert a sqlite3.Row to a dict."""
    if row is None:
        return None
    return dict(row)


# ── Sprint Repository ────────────────────────────────────────────────

class SprintRepository:
    """CRUD operations for the sprints table."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, sprint: SprintRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO sprints
                    (sprint_id, status, prompt, epic_id, issues_total, issues_done,
                     pid, error, created_at, started_at, paused_at, completed_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sprint.sprint_id, sprint.status, sprint.prompt, sprint.epic_id,
                    sprint.issues_total, sprint.issues_done, sprint.pid, sprint.error,
                    sprint.created_at, sprint.started_at, sprint.paused_at,
                    sprint.completed_at, sprint.updated_at,
                ),
            )
            return cursor.lastrowid

    def get(self, sprint_id: str) -> Optional[Dict]:
        row = self.db.fetchone(
            "SELECT * FROM sprints WHERE sprint_id = ?", (sprint_id,)
        )
        return _row_to_dict(row)

    def get_latest(self) -> Optional[Dict]:
        row = self.db.fetchone(
            "SELECT * FROM sprints ORDER BY created_at DESC LIMIT 1"
        )
        return _row_to_dict(row)

    def list_all(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        if status:
            rows = self.db.fetchall(
                "SELECT * FROM sprints WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM sprints ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def update_status(self, sprint_id: str, status: str, **kwargs) -> None:
        fields = ["status = ?", "updated_at = ?"]
        params = [status, _now()]

        timestamp_map = {
            "running": "started_at",
            "paused": "paused_at",
            "completed": "completed_at",
            "failed": "completed_at",
        }
        ts_field = timestamp_map.get(status)
        if ts_field:
            fields.append(f"{ts_field} = ?")
            params.append(_now())

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            params.append(value)

        params.append(sprint_id)
        sql = f"UPDATE sprints SET {', '.join(fields)} WHERE sprint_id = ?"

        with self.db.transaction():
            self.db.conn.execute(sql, tuple(params))

    def update_progress(self, sprint_id: str, issues_total: int, issues_done: int) -> None:
        with self.db.transaction():
            self.db.conn.execute(
                """
                UPDATE sprints SET issues_total = ?, issues_done = ?, updated_at = ?
                WHERE sprint_id = ?
                """,
                (issues_total, issues_done, _now(), sprint_id),
            )

    def delete(self, sprint_id: str) -> None:
        with self.db.transaction():
            self.db.conn.execute(
                "DELETE FROM sprints WHERE sprint_id = ?", (sprint_id,)
            )


# ── Epic Repository ──────────────────────────────────────────────────

class EpicRepository:
    """CRUD operations for the epics table."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, epic: EpicRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO epics (epic_id, sprint_id, status, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (epic.epic_id, epic.sprint_id, epic.status, epic.metadata,
                 epic.created_at, epic.updated_at),
            )
            return cursor.lastrowid

    def get(self, epic_id: str) -> Optional[Dict]:
        row = self.db.fetchone(
            "SELECT * FROM epics WHERE epic_id = ?", (epic_id,)
        )
        return _row_to_dict(row)

    def list_by_sprint(self, sprint_id: str) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM epics WHERE sprint_id = ? ORDER BY created_at",
            (sprint_id,),
        )
        return [dict(r) for r in rows]

    def update_status(self, epic_id: str, status: str, metadata: Optional[str] = None) -> None:
        with self.db.transaction():
            if metadata is not None:
                self.db.conn.execute(
                    "UPDATE epics SET status = ?, metadata = ?, updated_at = ? WHERE epic_id = ?",
                    (status, metadata, _now(), epic_id),
                )
            else:
                self.db.conn.execute(
                    "UPDATE epics SET status = ?, updated_at = ? WHERE epic_id = ?",
                    (status, _now(), epic_id),
                )


# ── Issue Repository ─────────────────────────────────────────────────

class IssueRepository:
    """CRUD operations for the issues table."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, issue: IssueRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO issues
                    (issue_number, epic_id, sprint_id, status, assigned_agent,
                     branch_name, pr_number, review_cycles, qa_cycles,
                     self_fix_attempts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    issue.issue_number, issue.epic_id, issue.sprint_id, issue.status,
                    issue.assigned_agent, issue.branch_name, issue.pr_number,
                    issue.review_cycles, issue.qa_cycles, issue.self_fix_attempts,
                    issue.created_at, issue.updated_at,
                ),
            )
            return cursor.lastrowid

    def get(self, issue_id: int) -> Optional[Dict]:
        row = self.db.fetchone("SELECT * FROM issues WHERE id = ?", (issue_id,))
        return _row_to_dict(row)

    def get_by_number(self, issue_number: int, epic_id: str) -> Optional[Dict]:
        row = self.db.fetchone(
            "SELECT * FROM issues WHERE issue_number = ? AND epic_id = ?",
            (issue_number, epic_id),
        )
        return _row_to_dict(row)

    def list_by_epic(self, epic_id: str) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM issues WHERE epic_id = ? ORDER BY issue_number",
            (epic_id,),
        )
        return [dict(r) for r in rows]

    def list_by_sprint(self, sprint_id: str, status: Optional[str] = None) -> List[Dict]:
        if status:
            rows = self.db.fetchall(
                "SELECT * FROM issues WHERE sprint_id = ? AND status = ? ORDER BY issue_number",
                (sprint_id, status),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM issues WHERE sprint_id = ? ORDER BY issue_number",
                (sprint_id,),
            )
        return [dict(r) for r in rows]

    def update_status(self, issue_id: int, status: str, **kwargs) -> None:
        fields = ["status = ?", "updated_at = ?"]
        params = [status, _now()]

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            params.append(value)

        params.append(issue_id)
        sql = f"UPDATE issues SET {', '.join(fields)} WHERE id = ?"

        with self.db.transaction():
            self.db.conn.execute(sql, tuple(params))

    def increment_cycles(self, issue_id: int, cycle_type: str) -> None:
        """Increment review_cycles, qa_cycles, or self_fix_attempts."""
        valid = {"review_cycles", "qa_cycles", "self_fix_attempts"}
        if cycle_type not in valid:
            raise ValueError(f"Invalid cycle_type: {cycle_type}. Must be one of {valid}")

        with self.db.transaction():
            self.db.conn.execute(
                f"UPDATE issues SET {cycle_type} = {cycle_type} + 1, updated_at = ? WHERE id = ?",
                (_now(), issue_id),
            )


# ── Cycle Repository ─────────────────────────────────────────────────

class CycleRepository:
    """CRUD operations for the cycles (workflow transitions) table."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, cycle: CycleRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO cycles (issue_id, cycle_number, agent_from, agent_to, action, result, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle.issue_id, cycle.cycle_number, cycle.agent_from,
                    cycle.agent_to, cycle.action, cycle.result, cycle.timestamp,
                ),
            )
            return cursor.lastrowid

    def list_by_issue(self, issue_id: int) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM cycles WHERE issue_id = ? ORDER BY cycle_number",
            (issue_id,),
        )
        return [dict(r) for r in rows]

    def get_latest(self, issue_id: int) -> Optional[Dict]:
        row = self.db.fetchone(
            "SELECT * FROM cycles WHERE issue_id = ? ORDER BY cycle_number DESC LIMIT 1",
            (issue_id,),
        )
        return _row_to_dict(row)


# ── Agent Message Repository ─────────────────────────────────────────

class MessageRepository:
    """CRUD for agent_messages — console output, communication, streaming."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, msg: AgentMessageRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO agent_messages
                    (sprint_id, agent_id, message_type, content, epic_id, issue_id,
                     level, related_agent, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg.sprint_id, msg.agent_id, msg.message_type, msg.content,
                    msg.epic_id, msg.issue_id, msg.level, msg.related_agent,
                    msg.metadata, msg.timestamp,
                ),
            )
            return cursor.lastrowid

    def create_batch(self, messages: List[AgentMessageRow]) -> int:
        """Insert multiple messages in a single transaction."""
        with self.db.transaction():
            self.db.conn.executemany(
                """
                INSERT INTO agent_messages
                    (sprint_id, agent_id, message_type, content, epic_id, issue_id,
                     level, related_agent, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (m.sprint_id, m.agent_id, m.message_type, m.content,
                     m.epic_id, m.issue_id, m.level, m.related_agent,
                     m.metadata, m.timestamp)
                    for m in messages
                ],
            )
            return len(messages)

    def get_by_agent(
        self,
        sprint_id: str,
        agent_id: str,
        since: Optional[str] = None,
        limit: int = 200,
        message_type: Optional[str] = None,
    ) -> List[Dict]:
        """Get messages for a specific agent, optionally filtered."""
        conditions = ["sprint_id = ?", "agent_id = ?"]
        params: list = [sprint_id, agent_id]

        if since:
            conditions.append("timestamp > ?")
            params.append(since)
        if message_type:
            conditions.append("message_type = ?")
            params.append(message_type)

        where = " AND ".join(conditions)
        params.append(limit)

        rows = self.db.fetchall(
            f"SELECT * FROM agent_messages WHERE {where} ORDER BY timestamp ASC LIMIT ?",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_by_sprint(
        self,
        sprint_id: str,
        since: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict]:
        """Get all messages for a sprint (cross-agent timeline)."""
        if since:
            rows = self.db.fetchall(
                """
                SELECT * FROM agent_messages
                WHERE sprint_id = ? AND timestamp > ?
                ORDER BY timestamp ASC LIMIT ?
                """,
                (sprint_id, since, limit),
            )
        else:
            rows = self.db.fetchall(
                """
                SELECT * FROM agent_messages
                WHERE sprint_id = ?
                ORDER BY timestamp ASC LIMIT ?
                """,
                (sprint_id, limit),
            )
        return [dict(r) for r in rows]

    def get_by_issue(self, issue_id: int, limit: int = 200) -> List[Dict]:
        rows = self.db.fetchall(
            """
            SELECT * FROM agent_messages
            WHERE issue_id = ?
            ORDER BY timestamp ASC LIMIT ?
            """,
            (issue_id, limit),
        )
        return [dict(r) for r in rows]

    def count_by_type(self, sprint_id: str) -> Dict[str, int]:
        """Get message count per type for a sprint."""
        rows = self.db.fetchall(
            """
            SELECT message_type, COUNT(*) as cnt
            FROM agent_messages WHERE sprint_id = ?
            GROUP BY message_type
            """,
            (sprint_id,),
        )
        return {row["message_type"]: row["cnt"] for row in rows}


# ── Agent Log Repository ─────────────────────────────────────────────

class LogRepository:
    """CRUD for agent_logs — structured event logging."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, log: AgentLogRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO agent_logs (sprint_id, agent_id, event, level, data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (log.sprint_id, log.agent_id, log.event, log.level,
                 log.data, log.timestamp),
            )
            return cursor.lastrowid

    def get_by_agent(
        self,
        sprint_id: str,
        agent_id: str,
        level: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict]:
        conditions = ["sprint_id = ?", "agent_id = ?"]
        params: list = [sprint_id, agent_id]

        if level:
            conditions.append("level = ?")
            params.append(level)

        where = " AND ".join(conditions)
        params.append(limit)

        # Use subquery to get last N rows, then order ASC for chronological output
        rows = self.db.fetchall(
            f"""SELECT * FROM (
                SELECT * FROM agent_logs WHERE {where}
                ORDER BY timestamp DESC LIMIT ?
            ) sub ORDER BY timestamp ASC""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_by_sprint(self, sprint_id: str, limit: int = 500) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM agent_logs WHERE sprint_id = ? ORDER BY timestamp ASC LIMIT ?",
            (sprint_id, limit),
        )
        return [dict(r) for r in rows]

    def get_timeline(
        self,
        sprint_id: str,
        agent_id: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict]:
        """
        Get a merged timeline of logs and messages for a sprint.

        Returns unified list sorted by timestamp.
        """
        if agent_id:
            logs = self.db.fetchall(
                """
                SELECT 'log' as source, agent_id, event as content, level,
                       data as metadata, timestamp
                FROM agent_logs
                WHERE sprint_id = ? AND agent_id = ?
                """,
                (sprint_id, agent_id),
            )
            messages = self.db.fetchall(
                """
                SELECT 'message' as source, agent_id, content, level,
                       metadata, timestamp
                FROM agent_messages
                WHERE sprint_id = ? AND agent_id = ?
                """,
                (sprint_id, agent_id),
            )
        else:
            logs = self.db.fetchall(
                """
                SELECT 'log' as source, agent_id, event as content, level,
                       data as metadata, timestamp
                FROM agent_logs WHERE sprint_id = ?
                """,
                (sprint_id,),
            )
            messages = self.db.fetchall(
                """
                SELECT 'message' as source, agent_id, content, level,
                       metadata, timestamp
                FROM agent_messages WHERE sprint_id = ?
                """,
                (sprint_id,),
            )

        # Merge and sort
        combined = [dict(r) for r in logs] + [dict(r) for r in messages]
        combined.sort(key=lambda x: x["timestamp"])
        return combined[:limit]


# ── Scorecard Repository ─────────────────────────────────────────────

class ScorecardRepository:
    """CRUD for issue_scorecards — ABD evaluation."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, sc: ScorecardRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO issue_scorecards
                    (issue_id, agent_id, scope_control, behavior_fidelity,
                     evidence_orientation, actionability, risk_awareness,
                     total, interpretation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sc.issue_id, sc.agent_id, sc.scope_control, sc.behavior_fidelity,
                    sc.evidence_orientation, sc.actionability, sc.risk_awareness,
                    sc.total, sc.interpretation, sc.created_at,
                ),
            )
            return cursor.lastrowid

    def get_by_issue(self, issue_id: int) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM issue_scorecards WHERE issue_id = ? ORDER BY created_at",
            (issue_id,),
        )
        return [dict(r) for r in rows]

    def get_latest_by_agent(self, agent_id: str, limit: int = 10) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM issue_scorecards WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit),
        )
        return [dict(r) for r in rows]

    def get_average_scores(self, agent_id: str) -> Optional[Dict]:
        row = self.db.fetchone(
            """
            SELECT
                AVG(scope_control) as avg_scope,
                AVG(behavior_fidelity) as avg_behavior,
                AVG(evidence_orientation) as avg_evidence,
                AVG(actionability) as avg_action,
                AVG(risk_awareness) as avg_risk,
                AVG(total) as avg_total,
                COUNT(*) as count
            FROM issue_scorecards WHERE agent_id = ?
            """,
            (agent_id,),
        )
        return _row_to_dict(row)


# ── Recycle Pattern Repository ───────────────────────────────────────

class RecycleRepository:
    """CRUD for issue_recycle_patterns."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create(self, rp: RecyclePatternRow) -> int:
        with self.db.transaction():
            cursor = self.db.conn.execute(
                """
                INSERT INTO issue_recycle_patterns
                    (issue_id, pattern_type, pattern_value, applied_by, applied_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rp.issue_id, rp.pattern_type, rp.pattern_value,
                 rp.applied_by, rp.applied_at),
            )
            return cursor.lastrowid

    def get_by_issue(self, issue_id: int) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM issue_recycle_patterns WHERE issue_id = ? ORDER BY applied_at",
            (issue_id,),
        )
        return [dict(r) for r in rows]

    def get_by_type(self, pattern_type: str, limit: int = 100) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM issue_recycle_patterns WHERE pattern_type = ? ORDER BY applied_at DESC LIMIT ?",
            (pattern_type, limit),
        )
        return [dict(r) for r in rows]

    def get_banned(self) -> List[Dict]:
        """Get all banned patterns (active anti-patterns)."""
        rows = self.db.fetchall(
            "SELECT DISTINCT pattern_value FROM issue_recycle_patterns WHERE pattern_type = 'banned'"
        )
        return [dict(r) for r in rows]


