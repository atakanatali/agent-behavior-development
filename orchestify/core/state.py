"""
State persistence module for ABD orchestration engine.

Tracks workflow state per epic with thread-safe persistence to `.orchestify/state.json`.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum


class IssueStatus(str, Enum):
    """Issue status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    QA = "qa"
    DONE = "done"
    ESCALATED = "escalated"


class EpicStatus(str, Enum):
    """Epic status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class CycleState:
    """Represents a single cycle in the workflow."""
    cycle_number: int
    agent_from: str
    agent_to: str
    action: str
    result: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CycleState":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class IssueState:
    """Represents the state of a single issue."""
    issue_number: int
    status: IssueStatus = IssueStatus.PENDING
    assigned_agent: Optional[str] = None
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None
    review_cycles: int = 0
    qa_cycles: int = 0
    self_fix_attempts: int = 0
    scorecard: Dict[str, Any] = field(default_factory=dict)
    recycle_output: Dict[str, List[str]] = field(default_factory=lambda: {
        "kept": [],
        "reused": [],
        "banned": []
    })
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cycle_history: List[CycleState] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["cycle_history"] = [cycle.to_dict() for cycle in self.cycle_history]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IssueState":
        """Create from dictionary."""
        if isinstance(data.get("status"), str):
            data["status"] = IssueStatus(data["status"])
        if data.get("cycle_history"):
            data["cycle_history"] = [
                CycleState.from_dict(c) for c in data["cycle_history"]
            ]
        return cls(**data)


@dataclass
class EpicState:
    """Represents the state of an epic."""
    epic_id: str
    status: EpicStatus = EpicStatus.PENDING
    issues: List[IssueState] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "epic_id": self.epic_id,
            "status": self.status.value,
            "issues": [issue.to_dict() for issue in self.issues],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpicState":
        """Create from dictionary."""
        if isinstance(data.get("status"), str):
            data["status"] = EpicStatus(data["status"])
        if data.get("issues"):
            data["issues"] = [IssueState.from_dict(i) for i in data["issues"]]
        return cls(**data)


class StateManager:
    """Thread-safe state manager for epic workflows."""

    def __init__(self, repo_root: Path):
        """
        Initialize state manager.

        Args:
            repo_root: Root path of the target repository
        """
        self.repo_root = Path(repo_root)
        self.state_dir = self.repo_root / ".orchestify"
        self.state_file = self.state_dir / "state.json"
        self._lock = threading.RLock()
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        self.state_dir.mkdir(exist_ok=True)

    def load(self) -> Dict[str, EpicState]:
        """
        Load all epic states from disk.

        Returns:
            Dictionary mapping epic_id to EpicState
        """
        with self._lock:
            if not self.state_file.exists():
                return {}

            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                return {
                    epic_id: EpicState.from_dict(epic_data)
                    for epic_id, epic_data in data.items()
                }
            except (json.JSONDecodeError, IOError) as e:
                raise RuntimeError(f"Failed to load state: {e}")

    def save(self) -> None:
        """Save current state to disk."""
        # This will be called by update methods
        pass

    def _persist_state(self, state: Dict[str, EpicState]) -> None:
        """
        Persist state dictionary to disk.

        Args:
            state: Dictionary mapping epic_id to EpicState
        """
        with self._lock:
            try:
                data = {
                    epic_id: epic.to_dict()
                    for epic_id, epic in state.items()
                }
                with open(self.state_file, "w") as f:
                    json.dump(data, f, indent=2)
            except IOError as e:
                raise RuntimeError(f"Failed to persist state: {e}")

    def get_epic(self, epic_id: str) -> Optional[EpicState]:
        """
        Get epic state by ID.

        Args:
            epic_id: Epic identifier

        Returns:
            EpicState or None if not found
        """
        state = self.load()
        return state.get(epic_id)

    def create_epic(self, epic_id: str) -> EpicState:
        """
        Create a new epic state.

        Args:
            epic_id: Epic identifier

        Returns:
            Created EpicState
        """
        with self._lock:
            state = self.load()
            if epic_id in state:
                return state[epic_id]

            epic = EpicState(epic_id=epic_id)
            state[epic_id] = epic
            self._persist_state(state)
            return epic

    def update_issue(
        self, epic_id: str, issue_number: int, data: Dict[str, Any]
    ) -> IssueState:
        """
        Update or create an issue in an epic.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            data: Fields to update

        Returns:
            Updated IssueState
        """
        with self._lock:
            state = self.load()
            if epic_id not in state:
                state[epic_id] = EpicState(epic_id=epic_id)

            epic = state[epic_id]

            # Find or create issue
            issue = None
            for iss in epic.issues:
                if iss.issue_number == issue_number:
                    issue = iss
                    break

            if issue is None:
                issue = IssueState(issue_number=issue_number)
                epic.issues.append(issue)

            # Update fields
            for key, value in data.items():
                if hasattr(issue, key):
                    if key == "status" and isinstance(value, str):
                        setattr(issue, key, IssueStatus(value))
                    else:
                        setattr(issue, key, value)

            issue.updated_at = datetime.utcnow().isoformat()
            epic.updated_at = datetime.utcnow().isoformat()

            self._persist_state(state)
            return issue

    def add_cycle(
        self,
        epic_id: str,
        issue_number: int,
        agent_from: str,
        agent_to: str,
        action: str,
        result: str,
    ) -> CycleState:
        """
        Add a cycle record to an issue's history.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            agent_from: Agent performing action
            agent_to: Next agent in cycle
            action: Action description
            result: Action result

        Returns:
            Created CycleState
        """
        with self._lock:
            state = self.load()
            if epic_id not in state:
                raise ValueError(f"Epic {epic_id} not found")

            epic = state[epic_id]
            issue = None
            for iss in epic.issues:
                if iss.issue_number == issue_number:
                    issue = iss
                    break

            if issue is None:
                raise ValueError(f"Issue {issue_number} not found in epic {epic_id}")

            cycle_number = len(issue.cycle_history) + 1
            cycle = CycleState(
                cycle_number=cycle_number,
                agent_from=agent_from,
                agent_to=agent_to,
                action=action,
                result=result,
            )
            issue.cycle_history.append(cycle)
            issue.updated_at = datetime.utcnow().isoformat()
            epic.updated_at = datetime.utcnow().isoformat()

            self._persist_state(state)
            return cycle

    def get_next_issue(self, epic_id: str) -> Optional[IssueState]:
        """
        Get the next pending issue in an epic.

        Args:
            epic_id: Epic identifier

        Returns:
            Next pending IssueState or None
        """
        epic = self.get_epic(epic_id)
        if not epic:
            return None

        for issue in epic.issues:
            if issue.status == IssueStatus.PENDING:
                return issue

        return None

    def is_epic_complete(self, epic_id: str) -> bool:
        """
        Check if all issues in an epic are complete.

        Args:
            epic_id: Epic identifier

        Returns:
            True if all issues are done or escalated
        """
        epic = self.get_epic(epic_id)
        if not epic or not epic.issues:
            return False

        for issue in epic.issues:
            if issue.status not in (IssueStatus.DONE, IssueStatus.ESCALATED):
                return False

        return True

    def update_epic_status(self, epic_id: str, status: EpicStatus) -> EpicState:
        """
        Update epic status.

        Args:
            epic_id: Epic identifier
            status: New status

        Returns:
            Updated EpicState
        """
        with self._lock:
            state = self.load()
            if epic_id not in state:
                raise ValueError(f"Epic {epic_id} not found")

            epic = state[epic_id]
            epic.status = status
            epic.updated_at = datetime.utcnow().isoformat()
            self._persist_state(state)
            return epic
