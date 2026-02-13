"""
Sprint management for orchestify.

Each sprint is an isolated execution context stored in .orchestify/<sprint_id>/.
Multiple sprints can run in parallel from different terminals.
"""
import json
import os
import random
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# Readable sprint ID components
_ADJECTIVES = [
    "swift", "bold", "calm", "deep", "fast", "keen", "neat", "pure",
    "safe", "warm", "wise", "cool", "fair", "firm", "free", "glad",
    "gold", "kind", "live", "mild", "open", "rare", "real", "rich",
]

_NOUNS = [
    "arch", "beam", "bolt", "core", "dart", "edge", "flux", "gate",
    "helm", "iris", "jade", "knot", "lens", "mesh", "node", "oath",
    "peak", "quay", "reef", "spur", "tide", "volt", "wave", "apex",
]


def generate_sprint_id() -> str:
    """
    Generate a readable sprint ID.

    Format: <adjective>-<noun>-<4digits>
    Example: swift-core-4821
    """
    adj = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    num = random.randint(1000, 9999)
    return f"{adj}-{noun}-{num}"


class Sprint:
    """Represents a single sprint execution context."""

    def __init__(self, sprint_dir: Path):
        self.sprint_dir = sprint_dir
        self.sprint_id = sprint_dir.name
        self.config_file = sprint_dir / "config.yaml"
        self.state_file = sprint_dir / "state.json"
        self.log_dir = sprint_dir / "logs"
        self.artifacts_dir = sprint_dir / "artifacts"

    @property
    def exists(self) -> bool:
        return self.sprint_dir.exists()

    def load_state(self) -> Dict[str, Any]:
        """Load sprint state."""
        if not self.state_file.exists():
            return {"status": "created", "started_at": None, "issues": []}
        with open(self.state_file, "r") as f:
            return json.load(f)

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save sprint state."""
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def load_config(self) -> Dict[str, Any]:
        """Load sprint-level config overrides."""
        if not self.config_file.exists():
            return {}
        with open(self.config_file, "r") as f:
            return yaml.safe_load(f) or {}

    def get_log_file(self, agent_id: str) -> Path:
        """Get the log file path for an agent."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return self.log_dir / f"{agent_id}.log"

    def get_task_file(self, agent_id: str) -> Path:
        """Get the task checkpoint YAML for an agent."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return self.log_dir / f"{agent_id}_task.yaml"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to summary dict."""
        state = self.load_state()
        return {
            "sprint_id": self.sprint_id,
            "status": state.get("status", "unknown"),
            "started_at": state.get("started_at"),
            "paused_at": state.get("paused_at"),
            "completed_at": state.get("completed_at"),
        }


class SprintManager:
    """Manages sprint lifecycle within a project."""

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.orchestify_dir = self.repo_root / ".orchestify"

    def create(self, sprint_id: Optional[str] = None, prompt: Optional[str] = None) -> Sprint:
        """
        Create a new sprint.

        Args:
            sprint_id: Optional custom sprint ID (auto-generated if None)
            prompt: Optional initial prompt/goal for the sprint

        Returns:
            Created Sprint instance
        """
        if sprint_id is None:
            sprint_id = generate_sprint_id()

        sprint_dir = self.orchestify_dir / sprint_id
        sprint_dir.mkdir(parents=True, exist_ok=True)

        sprint = Sprint(sprint_dir)

        # Create directory structure
        sprint.log_dir.mkdir(parents=True, exist_ok=True)
        sprint.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (sprint_dir / "personas").mkdir(exist_ok=True)
        (sprint_dir / "rules").mkdir(exist_ok=True)
        (sprint_dir / "prompts").mkdir(exist_ok=True)

        # Initialize state
        state = {
            "status": "created",
            "sprint_id": sprint_id,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "paused_at": None,
            "completed_at": None,
            "prompt": prompt,
            "epic_id": None,
            "issues_total": 0,
            "issues_done": 0,
            "pid": None,
        }
        sprint.save_state(state)

        # Write sprint config
        sprint_config = {
            "sprint_id": sprint_id,
            "created_at": datetime.utcnow().isoformat(),
            "overrides": {},
        }
        with open(sprint.config_file, "w") as f:
            yaml.dump(sprint_config, f, default_flow_style=False)

        return sprint

    def get(self, sprint_id: str) -> Optional[Sprint]:
        """Get a sprint by ID."""
        sprint_dir = self.orchestify_dir / sprint_id
        if not sprint_dir.exists():
            return None
        return Sprint(sprint_dir)

    def list_sprints(self) -> List[Sprint]:
        """List all sprints in the project."""
        if not self.orchestify_dir.exists():
            return []

        sprints = []
        for item in sorted(self.orchestify_dir.iterdir()):
            if item.is_dir() and (item / "state.json").exists():
                sprints.append(Sprint(item))
        return sprints

    def get_active_sprint(self) -> Optional[Sprint]:
        """Get the currently running sprint (if any)."""
        for sprint in self.list_sprints():
            state = sprint.load_state()
            if state.get("status") in ("running", "created"):
                # Check if PID is still alive
                pid = state.get("pid")
                if pid and self._is_process_alive(pid):
                    return sprint
                elif state.get("status") == "running":
                    # Process died, mark as paused
                    state["status"] = "paused"
                    state["paused_at"] = datetime.utcnow().isoformat()
                    sprint.save_state(state)
        return None

    def get_latest_sprint(self) -> Optional[Sprint]:
        """Get the most recently created sprint."""
        sprints = self.list_sprints()
        if not sprints:
            return None
        return sprints[-1]

    def pause(self, sprint_id: str) -> bool:
        """Pause a running sprint."""
        sprint = self.get(sprint_id)
        if not sprint:
            return False
        state = sprint.load_state()
        if state.get("status") != "running":
            return False
        state["status"] = "paused"
        state["paused_at"] = datetime.utcnow().isoformat()
        sprint.save_state(state)
        return True

    def resume(self, sprint_id: str) -> bool:
        """Resume a paused sprint."""
        sprint = self.get(sprint_id)
        if not sprint:
            return False
        state = sprint.load_state()
        if state.get("status") != "paused":
            return False
        state["status"] = "running"
        state["paused_at"] = None
        state["pid"] = os.getpid()
        sprint.save_state(state)
        return True

    def complete(self, sprint_id: str) -> bool:
        """Mark a sprint as complete."""
        sprint = self.get(sprint_id)
        if not sprint:
            return False
        state = sprint.load_state()
        state["status"] = "complete"
        state["completed_at"] = datetime.utcnow().isoformat()
        sprint.save_state(state)
        return True

    def update_gitignore(self) -> None:
        """Ensure .orchestify is properly handled in .gitignore."""
        gitignore = self.repo_root / ".gitignore"
        entries = [
            "# Orchestify runtime data",
            ".orchestify/*/logs/",
            ".orchestify/*/artifacts/",
            ".orchestify/*/state.json",
        ]

        existing = ""
        if gitignore.exists():
            existing = gitignore.read_text()

        additions = []
        for entry in entries:
            if entry not in existing:
                additions.append(entry)

        if additions:
            with open(gitignore, "a") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(additions) + "\n")

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if a process is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
