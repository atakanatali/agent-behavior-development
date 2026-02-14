"""
State persistence module for ABD orchestration engine.

Tracks workflow state per epic. All data stored in SQLite — no file-based state.
"""

import json
from datetime import datetime
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
    """State manager for epic workflows. All data stored in SQLite."""

    def __init__(self, db, sprint_id: str):
        """
        Initialize state manager.

        Args:
            db: DatabaseManager instance (required)
            sprint_id: Sprint ID for DB context (required)
        """
        self._db = db
        self._sprint_id = sprint_id

        from orchestify.db.repositories import (
            EpicRepository,
            IssueRepository,
            CycleRepository,
        )
        self._epic_repo = EpicRepository(db)
        self._issue_repo = IssueRepository(db)
        self._cycle_repo = CycleRepository(db)

    def get_epic(self, epic_id: str) -> Optional[EpicState]:
        """Get epic state by ID."""
        row = self._epic_repo.get(epic_id)
        if not row:
            return None

        # Build EpicState from DB
        epic = EpicState(
            epic_id=epic_id,
            status=EpicStatus(row.get("status", "pending")),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

        # Load issues for this epic
        issue_rows = self._issue_repo.list_by_sprint(self._sprint_id)
        for ir in issue_rows:
            if ir.get("epic_id") == epic_id:
                issue = IssueState(
                    issue_number=ir["issue_number"],
                    status=IssueStatus(ir.get("status", "pending")),
                    assigned_agent=ir.get("assigned_agent"),
                    branch_name=ir.get("branch_name"),
                    pr_number=ir.get("pr_number"),
                    review_cycles=ir.get("review_cycles", 0),
                    qa_cycles=ir.get("qa_cycles", 0),
                    self_fix_attempts=ir.get("self_fix_attempts", 0),
                    created_at=ir.get("created_at", ""),
                    updated_at=ir.get("updated_at", ""),
                )
                
                # Load cycle history for this issue
                cycle_rows = self._cycle_repo.list_by_issue(ir["id"])
                for cr in cycle_rows:
                    cycle = CycleState(
                        cycle_number=cr["cycle_number"],
                        agent_from=cr["agent_from"],
                        agent_to=cr["agent_to"],
                        action=cr["action"],
                        result=cr["result"],
                        timestamp=cr.get("timestamp", ""),
                    )
                    issue.cycle_history.append(cycle)
                
                epic.issues.append(issue)

        return epic

    def create_epic(self, epic_id: str) -> EpicState:
        """Create a new epic state."""
        # Check if already exists
        existing = self._epic_repo.get(epic_id)
        if existing:
            return self.get_epic(epic_id)

        from orchestify.db.models import EpicRow
        row = EpicRow(
            epic_id=epic_id,
            sprint_id=self._sprint_id,
            status="pending",
        )
        self._epic_repo.create(row)

        return EpicState(epic_id=epic_id)

    def update_issue(
        self, epic_id: str, issue_number: int, data: Dict[str, Any]
    ) -> IssueState:
        """Update or create an issue in an epic."""
        # Ensure epic exists
        if not self._epic_repo.get(epic_id):
            self.create_epic(epic_id)

        # Check if issue exists in DB
        db_issue = self._issue_repo.get_by_number(issue_number, epic_id)

        status = data.get("status", "pending")
        if isinstance(status, IssueStatus):
            status = status.value

        if db_issue is None:
            # Create new issue
            from orchestify.db.models import IssueRow
            row = IssueRow(
                issue_number=issue_number,
                epic_id=epic_id,
                sprint_id=self._sprint_id,
                status=status,
                assigned_agent=data.get("assigned_agent"),
                branch_name=data.get("branch_name"),
                pr_number=data.get("pr_number"),
                review_cycles=data.get("review_cycles", 0),
                qa_cycles=data.get("qa_cycles", 0),
                self_fix_attempts=data.get("self_fix_attempts", 0),
            )
            self._issue_repo.create(row)
        else:
            # Update existing - build kwargs for all fields to update
            update_kwargs = {
                "assigned_agent": data.get("assigned_agent", db_issue.get("assigned_agent")),
                "branch_name": data.get("branch_name", db_issue.get("branch_name")),
                "pr_number": data.get("pr_number", db_issue.get("pr_number")),
            }
            
            # Add cycle updates if provided
            if "review_cycles" in data:
                update_kwargs["review_cycles"] = data["review_cycles"]
            if "qa_cycles" in data:
                update_kwargs["qa_cycles"] = data["qa_cycles"]
            if "self_fix_attempts" in data:
                update_kwargs["self_fix_attempts"] = data["self_fix_attempts"]
            
            self._issue_repo.update_status(
                db_issue["id"],
                status,
                **update_kwargs
            )

        # Build IssueState from current DB state
        updated = self._issue_repo.get_by_number(issue_number, epic_id)
        if updated:
            return IssueState(
                issue_number=updated["issue_number"],
                status=IssueStatus(updated.get("status", "pending")),
                assigned_agent=updated.get("assigned_agent"),
                branch_name=updated.get("branch_name"),
                pr_number=updated.get("pr_number"),
                review_cycles=updated.get("review_cycles", 0),
                qa_cycles=updated.get("qa_cycles", 0),
                self_fix_attempts=updated.get("self_fix_attempts", 0),
            )
        return IssueState(issue_number=issue_number)

    def add_cycle(
        self,
        epic_id: str,
        issue_number: int,
        agent_from: str,
        agent_to: str,
        action: str,
        result: str,
    ) -> CycleState:
        """Add a cycle record to an issue's history."""
        db_issue = self._issue_repo.get_by_number(issue_number, epic_id)
        if not db_issue:
            raise ValueError(f"Issue {issue_number} not found in epic {epic_id}")

        # Count existing cycles to determine cycle_number
        existing_cycles = self._cycle_repo.list_by_issue(db_issue["id"])
        cycle_number = len(existing_cycles) + 1

        from orchestify.db.models import CycleRow
        row = CycleRow(
            issue_id=db_issue["id"],
            cycle_number=cycle_number,
            agent_from=agent_from,
            agent_to=agent_to,
            action=action,
            result=result,
        )
        self._cycle_repo.create(row)

        return CycleState(
            cycle_number=cycle_number,
            agent_from=agent_from,
            agent_to=agent_to,
            action=action,
            result=result,
        )

    def get_next_issue(self, epic_id: str) -> Optional[IssueState]:
        """Get the next pending issue in an epic."""
        epic = self.get_epic(epic_id)
        if not epic:
            return None

        for issue in epic.issues:
            if issue.status == IssueStatus.PENDING:
                return issue

        return None

    def is_epic_complete(self, epic_id: str) -> bool:
        """Check if all issues in an epic are complete."""
        epic = self.get_epic(epic_id)
        if not epic or not epic.issues:
            return False

        for issue in epic.issues:
            if issue.status not in (IssueStatus.DONE, IssueStatus.ESCALATED):
                return False

        return True

    def update_epic_status(self, epic_id: str, status: EpicStatus) -> EpicState:
        """Update epic status."""
        if not self._epic_repo.get(epic_id):
            raise ValueError(f"Epic {epic_id} not found")
        self._epic_repo.update_status(epic_id, status.value)
        return self.get_epic(epic_id)
