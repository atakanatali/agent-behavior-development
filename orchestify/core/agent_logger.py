"""
Agent context logging system.

All logs are stored in SQLite (~/.orchestify/data/orchestify.db).
No file-based logging — DB is the single source of truth.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class AgentLogger:
    """
    Manages logging for agent execution.

    All data stored in SQLite via repository layer:
    - agent_logs: Structured event logs
    - agent_messages: Console output, inter-agent communication, checkpoints
    - issue_scorecards: ABD scorecard evaluations
    - issue_recycle_patterns: Kept/reused/banned patterns
    """

    def __init__(self, db, sprint_id: str):
        """
        Initialize the agent logger.

        Args:
            db: DatabaseManager instance (required)
            sprint_id: Sprint ID for DB records (required)
        """
        self._db = db
        self._sprint_id = sprint_id

        from orchestify.db.repositories import (
            LogRepository,
            MessageRepository,
            ScorecardRepository,
            RecycleRepository,
        )
        self._log_repo = LogRepository(db)
        self._msg_repo = MessageRepository(db)
        self._scorecard_repo = ScorecardRepository(db)
        self._recycle_repo = RecycleRepository(db)

    def log(
        self,
        agent_id: str,
        event: str,
        data: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
    ) -> None:
        """
        Log a structured event for an agent.

        Args:
            agent_id: Agent identifier
            event: Event description
            data: Optional structured data
            level: Log level (INFO, WARN, ERROR, DEBUG)
        """
        timestamp = datetime.utcnow().isoformat()

        try:
            from orchestify.db.models import AgentLogRow
            log_row = AgentLogRow(
                sprint_id=self._sprint_id,
                agent_id=agent_id,
                event=event,
                level=level,
                data=json.dumps(data) if data else None,
                timestamp=timestamp,
            )
            self._log_repo.create(log_row)
        except Exception:
            pass  # DB write failure shouldn't break the pipeline

    def log_output(
        self,
        agent_id: str,
        content: str,
        level: str = "INFO",
        message_type: str = "output",
        epic_id: Optional[str] = None,
        issue_id: Optional[int] = None,
        related_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log agent output to the messages table.

        Used for console streaming and inter-agent communication.
        """
        try:
            from orchestify.db.models import AgentMessageRow
            msg = AgentMessageRow(
                sprint_id=self._sprint_id,
                agent_id=agent_id,
                message_type=message_type,
                content=content,
                epic_id=epic_id,
                issue_id=issue_id,
                level=level,
                related_agent=related_agent,
                metadata=json.dumps(metadata) if metadata else None,
            )
            self._msg_repo.create(msg)
        except Exception:
            pass

    def log_context(
        self,
        agent_id: str,
        context: Dict[str, Any],
    ) -> None:
        """Log the full context given to an agent."""
        self.log(agent_id, "context_received", {
            "goal": context.get("goal", ""),
            "instructions_length": len(str(context.get("instructions", ""))),
            "touches": context.get("touches", []),
            "dependencies": context.get("dependencies", []),
        })

    def log_result(
        self,
        agent_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Log the result of an agent execution."""
        self.log(agent_id, "execution_complete", {
            "files_changed": result.get("files_changed", []),
            "tokens_used": result.get("tokens_used", 0),
            "duration": result.get("duration", 0),
            "output_length": len(str(result.get("output", ""))),
        })

    def log_scorecard(
        self,
        agent_id: str,
        scorecard: Dict[str, Any],
        issue_id: Optional[int] = None,
    ) -> None:
        """Log a scorecard evaluation."""
        self.log(agent_id, "scorecard_evaluated", scorecard)

        if issue_id is not None:
            try:
                from orchestify.db.models import ScorecardRow
                sc = ScorecardRow(
                    issue_id=issue_id,
                    agent_id=agent_id,
                    scope_control=scorecard.get("scope_control", 0),
                    behavior_fidelity=scorecard.get("behavior_fidelity", 0),
                    evidence_orientation=scorecard.get("evidence_orientation", 0),
                    actionability=scorecard.get("actionability", 0),
                    risk_awareness=scorecard.get("risk_awareness", 0),
                    total=scorecard.get("total", 0),
                    interpretation=scorecard.get("interpretation"),
                )
                self._scorecard_repo.create(sc)
            except Exception:
                pass

    def log_recycle(
        self,
        agent_id: str,
        recycle: Dict[str, Any],
        issue_id: Optional[int] = None,
    ) -> None:
        """Log a recycle operation."""
        self.log(agent_id, "recycle_applied", recycle)

        if issue_id is not None:
            try:
                from orchestify.db.models import RecyclePatternRow
                for pattern_type in ("kept", "reused", "banned"):
                    for value in recycle.get(pattern_type, []):
                        rp = RecyclePatternRow(
                            issue_id=issue_id,
                            pattern_type=pattern_type,
                            pattern_value=value,
                            applied_by=agent_id,
                        )
                        self._recycle_repo.create(rp)
            except Exception:
                pass

    def save_task_checkpoint(
        self,
        agent_id: str,
        task: Dict[str, Any],
    ) -> None:
        """Save current task checkpoint for resume capability (DB-only)."""
        checkpoint = {
            "agent_id": agent_id,
            "updated_at": datetime.utcnow().isoformat(),
            **task,
        }
        self.log_output(
            agent_id=agent_id,
            content=json.dumps(checkpoint),
            message_type="checkpoint",
        )

    def load_task_checkpoint(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load the latest task checkpoint for an agent from DB."""
        try:
            messages = self._msg_repo.get_by_agent(
                sprint_id=self._sprint_id,
                agent_id=agent_id,
                limit=1,
            )
            # Find latest checkpoint
            for msg in reversed(messages) if messages else []:
                if msg.get("message_type") == "checkpoint":
                    return json.loads(msg["content"])
            # Also try a direct query for checkpoints
            rows = self._db.fetchall(
                """SELECT content FROM agent_messages
                   WHERE sprint_id = ? AND agent_id = ? AND message_type = 'checkpoint'
                   ORDER BY timestamp DESC LIMIT 1""",
                (self._sprint_id, agent_id),
            )
            if rows:
                return json.loads(rows[0]["content"])
        except Exception:
            pass
        return None

    def get_agent_logs(
        self,
        agent_id: str,
        limit: int = 50,
        level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read recent log entries for an agent from DB."""
        try:
            rows = self._log_repo.get_by_agent(
                sprint_id=self._sprint_id,
                agent_id=agent_id,
                level=level,
                limit=limit,
            )
            # Parse JSON data field
            for row in rows:
                if row.get("data") and isinstance(row["data"], str):
                    try:
                        row["data"] = json.loads(row["data"])
                    except (json.JSONDecodeError, TypeError):
                        pass
            return rows
        except Exception:
            return []

    def get_all_agent_ids(self) -> List[str]:
        """Get all agent IDs that have logs."""
        try:
            rows = self._db.fetchall(
                """SELECT DISTINCT agent_id FROM agent_logs
                   WHERE sprint_id = ?
                   ORDER BY agent_id""",
                (self._sprint_id,),
            )
            return [r["agent_id"] for r in rows]
        except Exception:
            return []

    def get_timeline(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get a merged timeline of all agent activities."""
        try:
            return self._log_repo.get_timeline(
                sprint_id=self._sprint_id,
                limit=limit,
            )
        except Exception:
            return []
