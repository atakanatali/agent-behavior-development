"""
Agent context logging system.

Append-only timestamped log files + YAML task checkpoint files.
Each agent action is logged with full context for observability and resume capability.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class AgentLogger:
    """
    Manages append-only logging for agent execution.

    Each agent gets:
    - <agent_id>.log: Append-only timestamped log of all actions
    - <agent_id>_task.yaml: Current task checkpoint for resume capability
    """

    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        agent_id: str,
        event: str,
        data: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
    ) -> None:
        """
        Append a log entry for an agent.

        Args:
            agent_id: Agent identifier
            event: Event description
            data: Optional structured data
            level: Log level (INFO, WARN, ERROR, DEBUG)
        """
        log_file = self.log_dir / f"{agent_id}.log"
        timestamp = datetime.utcnow().isoformat()

        entry = {
            "timestamp": timestamp,
            "agent_id": agent_id,
            "level": level,
            "event": event,
        }
        if data:
            entry["data"] = data

        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_context(
        self,
        agent_id: str,
        context: Dict[str, Any],
    ) -> None:
        """
        Log the full context given to an agent.

        Args:
            agent_id: Agent identifier
            context: Agent execution context
        """
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
        """
        Log the result of an agent execution.

        Args:
            agent_id: Agent identifier
            result: Agent execution result
        """
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
    ) -> None:
        """
        Log a scorecard evaluation.

        Args:
            agent_id: Agent identifier
            scorecard: Scorecard data
        """
        self.log(agent_id, "scorecard_evaluated", scorecard)

    def log_recycle(
        self,
        agent_id: str,
        recycle: Dict[str, Any],
    ) -> None:
        """
        Log a recycle operation.

        Args:
            agent_id: Agent identifier
            recycle: Recycle output data
        """
        self.log(agent_id, "recycle_applied", recycle)

    def save_task_checkpoint(
        self,
        agent_id: str,
        task: Dict[str, Any],
    ) -> None:
        """
        Save current task checkpoint for resume capability.

        Args:
            agent_id: Agent identifier
            task: Current task state
        """
        task_file = self.log_dir / f"{agent_id}_task.yaml"
        checkpoint = {
            "agent_id": agent_id,
            "updated_at": datetime.utcnow().isoformat(),
            **task,
        }
        with open(task_file, "w") as f:
            yaml.dump(checkpoint, f, default_flow_style=False)

    def load_task_checkpoint(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Load the latest task checkpoint for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Task checkpoint data or None
        """
        task_file = self.log_dir / f"{agent_id}_task.yaml"
        if not task_file.exists():
            return None
        with open(task_file, "r") as f:
            return yaml.safe_load(f)

    def get_agent_logs(
        self,
        agent_id: str,
        limit: int = 50,
        level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read recent log entries for an agent.

        Args:
            agent_id: Agent identifier
            limit: Maximum entries to return
            level: Optional level filter

        Returns:
            List of log entries (most recent first)
        """
        log_file = self.log_dir / f"{agent_id}.log"
        if not log_file.exists():
            return []

        entries = []
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if level and entry.get("level") != level:
                        continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

        return entries[-limit:]

    def get_all_agent_ids(self) -> List[str]:
        """Get all agent IDs that have logs."""
        agent_ids = set()
        for log_file in self.log_dir.glob("*.log"):
            agent_ids.add(log_file.stem)
        return sorted(agent_ids)

    def get_timeline(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get a merged timeline of all agent activities.

        Returns entries sorted by timestamp (most recent first).
        """
        all_entries = []
        for agent_id in self.get_all_agent_ids():
            entries = self.get_agent_logs(agent_id)
            all_entries.extend(entries)

        all_entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return all_entries[:limit]
