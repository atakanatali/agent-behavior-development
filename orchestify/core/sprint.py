"""
Sprint management for orchestify.

Each sprint is an agent execution context / session — NOT a project sprint.
It tracks "where was I, what did I last do" for agents.
Real project sprints are tracked via GitHub issues by the architect agent.

All sprint data lives in SQLite (~/.orchestify/data/orchestify.db).
The only filesystem artifact is ~/.orchestify/artifacts/<sprint_id>/ for output files.
"""
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestify.core.global_config import get_orchestify_home


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
    """
    Represents a single sprint (agent execution context).

    Backed entirely by SQLite. The only filesystem path is artifacts_dir
    for storing output files.
    """

    def __init__(self, sprint_id: str, db, row: Optional[Dict[str, Any]] = None):
        """
        Initialize a Sprint.

        Args:
            sprint_id: Unique sprint identifier
            db: DatabaseManager instance (required)
            row: Optional pre-loaded DB row dict (avoids extra query)
        """
        self.sprint_id = sprint_id
        self._db = db
        self._row = row

        # Only physical directory — for output artifacts
        self.artifacts_dir = get_orchestify_home() / "artifacts" / sprint_id

    def _get_repo(self):
        from orchestify.db.repositories import SprintRepository
        return SprintRepository(self._db)

    def _ensure_row(self) -> Dict[str, Any]:
        """Load row from DB if not cached."""
        if self._row is None:
            repo = self._get_repo()
            self._row = repo.get(self.sprint_id)
        return self._row or {}

    @property
    def exists(self) -> bool:
        return self._ensure_row() != {}

    def load_state(self) -> Dict[str, Any]:
        """Load sprint state from DB (always re-fetches)."""
        # Always re-fetch to avoid stale cache
        self._row = None
        row = self._ensure_row()
        if not row:
            return {"status": "created", "started_at": None}
        return {
            "status": row.get("status", "unknown"),
            "sprint_id": row.get("sprint_id", self.sprint_id),
            "created_at": row.get("created_at"),
            "started_at": row.get("started_at"),
            "paused_at": row.get("paused_at"),
            "completed_at": row.get("completed_at"),
            "prompt": row.get("prompt"),
            "epic_id": row.get("epic_id"),
            "issues_total": row.get("issues_total", 0),
            "issues_done": row.get("issues_done", 0),
            "pid": row.get("pid"),
            "error": row.get("error"),
        }

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save sprint state to DB."""
        repo = self._get_repo()
        status = state.get("status", "created")
        kwargs = {}
        for key in ("pid", "prompt", "epic_id", "error"):
            if key in state:
                kwargs[key] = state[key]
        repo.update_status(self.sprint_id, status, **kwargs)
        if "issues_total" in state or "issues_done" in state:
            repo.update_progress(
                self.sprint_id,
                state.get("issues_total", 0),
                state.get("issues_done", 0),
            )
        # Invalidate cache
        self._row = None

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
    """
    Manages sprint lifecycle.

    All data lives in SQLite. No filesystem directories are created
    for sprints (except artifacts/).
    """

    def __init__(self, db):
        """
        Initialize sprint manager.

        Args:
            db: DatabaseManager instance (required)
        """
        self._db = db
        from orchestify.db.repositories import SprintRepository
        self._sprint_repo = SprintRepository(db)

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

        now = datetime.utcnow().isoformat()

        from orchestify.db.models import SprintRow
        row = SprintRow(
            sprint_id=sprint_id,
            status="created",
            prompt=prompt,
            created_at=now,
            updated_at=now,
        )
        self._sprint_repo.create(row)

        sprint = Sprint(sprint_id, self._db)

        # Create artifacts directory (only physical dir)
        sprint.artifacts_dir.mkdir(parents=True, exist_ok=True)

        return sprint

    def get(self, sprint_id: str) -> Optional[Sprint]:
        """Get a sprint by ID."""
        row = self._sprint_repo.get(sprint_id)
        if row is None:
            return None
        return Sprint(sprint_id, self._db, row=row)

    def list_sprints(self, status: Optional[str] = None) -> List[Sprint]:
        """List all sprints from DB."""
        rows = self._sprint_repo.list_all(status=status)
        return [Sprint(r["sprint_id"], self._db, row=r) for r in rows]

    def get_active_sprint(self) -> Optional[Sprint]:
        """Get the currently running sprint (if any)."""
        rows = self._sprint_repo.list_all(status="running")
        for row in rows:
            pid = row.get("pid")
            if pid and self._is_process_alive(pid):
                return Sprint(row["sprint_id"], self._db, row=row)
            else:
                # Process died, mark as paused
                self._sprint_repo.update_status(row["sprint_id"], "paused")

        # Also check "created" sprints
        rows = self._sprint_repo.list_all(status="created")
        if rows:
            return Sprint(rows[0]["sprint_id"], self._db, row=rows[0])

        return None

    def get_latest_sprint(self) -> Optional[Sprint]:
        """Get the most recently created sprint."""
        row = self._sprint_repo.get_latest()
        if row is None:
            return None
        return Sprint(row["sprint_id"], self._db, row=row)

    def pause(self, sprint_id: str) -> bool:
        """Pause a running sprint."""
        row = self._sprint_repo.get(sprint_id)
        if not row or row.get("status") != "running":
            return False
        self._sprint_repo.update_status(sprint_id, "paused")
        return True

    def resume(self, sprint_id: str) -> bool:
        """Resume a paused sprint."""
        row = self._sprint_repo.get(sprint_id)
        if not row or row.get("status") != "paused":
            return False
        self._sprint_repo.update_status(sprint_id, "running", pid=os.getpid())
        return True

    def complete(self, sprint_id: str) -> bool:
        """Mark a sprint as complete."""
        row = self._sprint_repo.get(sprint_id)
        if not row:
            return False
        self._sprint_repo.update_status(sprint_id, "completed")
        return True

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if a process is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
