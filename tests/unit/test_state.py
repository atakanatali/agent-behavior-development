"""Unit tests for orchestify.core.state module."""
import json
import threading
from pathlib import Path

import pytest

from orchestify.core.state import (
    CycleState,
    EpicState,
    EpicStatus,
    IssueState,
    IssueStatus,
    StateManager,
)


# ─── CycleState Tests ───


class TestCycleState:
    def test_create_cycle_state(self):
        cycle = CycleState(
            cycle_number=1,
            agent_from="engineer",
            agent_to="reviewer",
            action="Submit PR",
            result="PR created",
        )
        assert cycle.cycle_number == 1
        assert cycle.agent_from == "engineer"
        assert cycle.agent_to == "reviewer"
        assert cycle.timestamp is not None

    def test_to_dict(self):
        cycle = CycleState(
            cycle_number=1,
            agent_from="engineer",
            agent_to="reviewer",
            action="Submit PR",
            result="PR created",
        )
        d = cycle.to_dict()
        assert d["cycle_number"] == 1
        assert d["agent_from"] == "engineer"
        assert "timestamp" in d

    def test_from_dict(self):
        data = {
            "cycle_number": 2,
            "agent_from": "reviewer",
            "agent_to": "engineer",
            "action": "Request changes",
            "result": "Comments added",
            "timestamp": "2026-02-13T12:00:00",
        }
        cycle = CycleState.from_dict(data)
        assert cycle.cycle_number == 2
        assert cycle.agent_from == "reviewer"
        assert cycle.timestamp == "2026-02-13T12:00:00"

    def test_roundtrip_serialization(self):
        cycle = CycleState(
            cycle_number=1,
            agent_from="qa",
            agent_to="engineer",
            action="Bug found",
            result="Fix needed",
        )
        restored = CycleState.from_dict(cycle.to_dict())
        assert restored.cycle_number == cycle.cycle_number
        assert restored.agent_from == cycle.agent_from
        assert restored.result == cycle.result


# ─── IssueState Tests ───


class TestIssueState:
    def test_create_default_issue(self):
        issue = IssueState(issue_number=42)
        assert issue.issue_number == 42
        assert issue.status == IssueStatus.PENDING
        assert issue.assigned_agent is None
        assert issue.review_cycles == 0
        assert issue.qa_cycles == 0
        assert issue.recycle_output == {"kept": [], "reused": [], "banned": []}

    def test_create_with_status(self):
        issue = IssueState(issue_number=10, status=IssueStatus.IN_PROGRESS)
        assert issue.status == IssueStatus.IN_PROGRESS

    def test_to_dict(self):
        issue = IssueState(
            issue_number=42,
            status=IssueStatus.REVIEW,
            assigned_agent="engineer_frontend",
            pr_number=123,
            review_cycles=1,
        )
        d = issue.to_dict()
        assert d["issue_number"] == 42
        assert d["status"] == "review"
        assert d["assigned_agent"] == "engineer_frontend"
        assert d["pr_number"] == 123

    def test_from_dict_with_string_status(self):
        data = {
            "issue_number": 5,
            "status": "qa",
            "review_cycles": 2,
            "qa_cycles": 1,
        }
        issue = IssueState.from_dict(data)
        assert issue.status == IssueStatus.QA
        assert issue.review_cycles == 2

    def test_from_dict_with_cycle_history(self):
        data = {
            "issue_number": 5,
            "status": "in_progress",
            "cycle_history": [
                {
                    "cycle_number": 1,
                    "agent_from": "engineer",
                    "agent_to": "reviewer",
                    "action": "PR submitted",
                    "result": "OK",
                    "timestamp": "2026-02-13T10:00:00",
                }
            ],
        }
        issue = IssueState.from_dict(data)
        assert len(issue.cycle_history) == 1
        assert isinstance(issue.cycle_history[0], CycleState)

    def test_roundtrip_serialization(self):
        issue = IssueState(
            issue_number=42,
            status=IssueStatus.DONE,
            assigned_agent="engineer_backend",
            pr_number=55,
            review_cycles=2,
            qa_cycles=1,
        )
        restored = IssueState.from_dict(issue.to_dict())
        assert restored.issue_number == issue.issue_number
        assert restored.status == issue.status
        assert restored.pr_number == issue.pr_number


# ─── EpicState Tests ───


class TestEpicState:
    def test_create_epic(self):
        epic = EpicState(epic_id="epic-001")
        assert epic.epic_id == "epic-001"
        assert epic.status == EpicStatus.PENDING
        assert epic.issues == []

    def test_to_dict(self):
        epic = EpicState(
            epic_id="epic-001",
            status=EpicStatus.IN_PROGRESS,
            issues=[IssueState(issue_number=1), IssueState(issue_number=2)],
        )
        d = epic.to_dict()
        assert d["epic_id"] == "epic-001"
        assert d["status"] == "in_progress"
        assert len(d["issues"]) == 2

    def test_from_dict(self):
        data = {
            "epic_id": "epic-002",
            "status": "complete",
            "issues": [
                {"issue_number": 10, "status": "done"},
                {"issue_number": 11, "status": "done"},
            ],
            "created_at": "2026-02-13T10:00:00",
            "updated_at": "2026-02-13T12:00:00",
        }
        epic = EpicState.from_dict(data)
        assert epic.epic_id == "epic-002"
        assert epic.status == EpicStatus.COMPLETE
        assert len(epic.issues) == 2
        assert epic.issues[0].status == IssueStatus.DONE

    def test_roundtrip_serialization(self):
        epic = EpicState(
            epic_id="epic-003",
            status=EpicStatus.FAILED,
            issues=[
                IssueState(issue_number=1, status=IssueStatus.ESCALATED),
            ],
        )
        restored = EpicState.from_dict(epic.to_dict())
        assert restored.epic_id == epic.epic_id
        assert restored.status == epic.status
        assert len(restored.issues) == 1


# ─── IssueStatus Tests ───


class TestIssueStatus:
    def test_all_statuses_exist(self):
        assert IssueStatus.PENDING == "pending"
        assert IssueStatus.IN_PROGRESS == "in_progress"
        assert IssueStatus.REVIEW == "review"
        assert IssueStatus.QA == "qa"
        assert IssueStatus.DONE == "done"
        assert IssueStatus.ESCALATED == "escalated"

    def test_status_from_string(self):
        assert IssueStatus("pending") == IssueStatus.PENDING
        assert IssueStatus("done") == IssueStatus.DONE


class TestEpicStatus:
    def test_all_statuses_exist(self):
        assert EpicStatus.PENDING == "pending"
        assert EpicStatus.IN_PROGRESS == "in_progress"
        assert EpicStatus.COMPLETE == "complete"
        assert EpicStatus.FAILED == "failed"


# ─── StateManager Tests ───


class TestStateManager:
    def test_create_epic(self, state_manager):
        epic = state_manager.create_epic("epic-001")
        assert epic.epic_id == "epic-001"
        assert epic.status == EpicStatus.PENDING

    def test_create_epic_idempotent(self, state_manager):
        epic1 = state_manager.create_epic("epic-001")
        epic2 = state_manager.create_epic("epic-001")
        assert epic1.epic_id == epic2.epic_id

    def test_create_epic_persists(self, state_manager):
        state_manager.create_epic("epic-001")
        epic = state_manager.get_epic("epic-001")
        assert epic is not None
        assert epic.epic_id == "epic-001"

    def test_get_epic(self, state_manager):
        state_manager.create_epic("epic-001")
        epic = state_manager.get_epic("epic-001")
        assert epic is not None
        assert epic.epic_id == "epic-001"

    def test_get_epic_not_found(self, state_manager):
        epic = state_manager.get_epic("nonexistent")
        assert epic is None

    def test_update_issue_creates_new(self, state_manager):
        state_manager.create_epic("epic-001")
        issue = state_manager.update_issue(
            "epic-001", 42, {"status": IssueStatus.IN_PROGRESS, "assigned_agent": "engineer"}
        )
        assert issue.issue_number == 42
        assert issue.status == IssueStatus.IN_PROGRESS
        assert issue.assigned_agent == "engineer"

    def test_update_issue_creates_epic_if_missing(self, state_manager):
        issue = state_manager.update_issue("epic-new", 1, {"status": IssueStatus.PENDING})
        assert issue.issue_number == 1

    def test_update_issue_modifies_existing(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 42, {"status": IssueStatus.PENDING})
        issue = state_manager.update_issue(
            "epic-001", 42, {"status": IssueStatus.REVIEW, "review_cycles": 1}
        )
        assert issue.status == IssueStatus.REVIEW
        assert issue.review_cycles == 1

    def test_update_issue_string_status(self, state_manager):
        state_manager.create_epic("epic-001")
        issue = state_manager.update_issue("epic-001", 42, {"status": "qa"})
        assert issue.status == IssueStatus.QA

    def test_add_cycle(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 42, {})
        cycle = state_manager.add_cycle(
            "epic-001", 42, "engineer", "reviewer", "Submit PR", "OK"
        )
        assert cycle.cycle_number == 1
        assert cycle.agent_from == "engineer"

    def test_add_cycle_increments(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 42, {})
        state_manager.add_cycle("epic-001", 42, "engineer", "reviewer", "PR", "OK")
        cycle2 = state_manager.add_cycle("epic-001", 42, "reviewer", "engineer", "Fix", "Done")
        assert cycle2.cycle_number == 2

    def test_add_cycle_epic_not_found(self, state_manager):
        with pytest.raises(ValueError, match="Issue .* not found"):
            state_manager.add_cycle("nonexistent", 1, "a", "b", "c", "d")

    def test_add_cycle_issue_not_found(self, state_manager):
        state_manager.create_epic("epic-001")
        with pytest.raises(ValueError, match="Issue .* not found"):
            state_manager.add_cycle("epic-001", 999, "a", "b", "c", "d")

    def test_get_next_issue(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 1, {"status": IssueStatus.DONE})
        state_manager.update_issue("epic-001", 2, {"status": IssueStatus.PENDING})
        state_manager.update_issue("epic-001", 3, {"status": IssueStatus.PENDING})
        nxt = state_manager.get_next_issue("epic-001")
        assert nxt is not None
        assert nxt.issue_number == 2

    def test_get_next_issue_all_done(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 1, {"status": IssueStatus.DONE})
        state_manager.update_issue("epic-001", 2, {"status": IssueStatus.DONE})
        nxt = state_manager.get_next_issue("epic-001")
        assert nxt is None

    def test_get_next_issue_epic_not_found(self, state_manager):
        nxt = state_manager.get_next_issue("nonexistent")
        assert nxt is None

    def test_is_epic_complete_true(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 1, {"status": IssueStatus.DONE})
        state_manager.update_issue("epic-001", 2, {"status": IssueStatus.DONE})
        assert state_manager.is_epic_complete("epic-001") is True

    def test_is_epic_complete_with_escalated(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 1, {"status": IssueStatus.DONE})
        state_manager.update_issue("epic-001", 2, {"status": IssueStatus.ESCALATED})
        assert state_manager.is_epic_complete("epic-001") is True

    def test_is_epic_complete_false(self, state_manager):
        state_manager.create_epic("epic-001")
        state_manager.update_issue("epic-001", 1, {"status": IssueStatus.DONE})
        state_manager.update_issue("epic-001", 2, {"status": IssueStatus.IN_PROGRESS})
        assert state_manager.is_epic_complete("epic-001") is False

    def test_is_epic_complete_no_issues(self, state_manager):
        state_manager.create_epic("epic-001")
        assert state_manager.is_epic_complete("epic-001") is False

    def test_is_epic_complete_not_found(self, state_manager):
        assert state_manager.is_epic_complete("nonexistent") is False

    def test_update_epic_status(self, state_manager):
        state_manager.create_epic("epic-001")
        epic = state_manager.update_epic_status("epic-001", EpicStatus.COMPLETE)
        assert epic.status == EpicStatus.COMPLETE

    def test_update_epic_status_not_found(self, state_manager):
        with pytest.raises(ValueError, match="Epic .* not found"):
            state_manager.update_epic_status("nonexistent", EpicStatus.FAILED)

    def test_state_persistence_survives_reload(self, sprint_db):
        sm1 = StateManager(sprint_db, sprint_id="test-sprint")
        sm1.create_epic("epic-001")
        sm1.update_issue("epic-001", 42, {"status": IssueStatus.IN_PROGRESS})

        sm2 = StateManager(sprint_db, sprint_id="test-sprint")
        epic = sm2.get_epic("epic-001")
        assert epic is not None
        assert len(epic.issues) == 1
        assert epic.issues[0].issue_number == 42

    def test_thread_safety(self, tmp_path):
        """Test concurrent access to state manager (file-based DB for threads)."""
        from orchestify.db.database import DatabaseManager
        from orchestify.migrations.runner import MigrationRunner

        db_path = tmp_path / "thread_test.db"
        db = DatabaseManager(db_path)
        MigrationRunner(db).run_pending()

        # Create sprint for FK
        from orchestify.db.models import SprintRow
        from orchestify.db.repositories import SprintRepository
        SprintRepository(db).create(SprintRow(sprint_id="test-sprint", status="created"))

        sm = StateManager(db, sprint_id="test-sprint")
        sm.create_epic("epic-001")
        errors = []

        def create_issues(start, count):
            try:
                for i in range(start, start + count):
                    sm.update_issue("epic-001", i, {"status": IssueStatus.PENDING})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_issues, args=(1, 5)),
            threading.Thread(target=create_issues, args=(100, 5)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        epic = sm.get_epic("epic-001")
        assert epic is not None
        assert len(epic.issues) == 10
