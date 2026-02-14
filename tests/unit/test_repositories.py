"""Tests for orchestify.db.repositories — Repository CRUD operations."""
import json
from pathlib import Path

import pytest

from orchestify.db.database import DatabaseManager
from orchestify.db.models import (
    SprintRow, EpicRow, IssueRow, CycleRow,
    AgentMessageRow, AgentLogRow, ScorecardRow,
    RecyclePatternRow,
)
from orchestify.db.repositories import (
    SprintRepository, EpicRepository, IssueRepository,
    CycleRepository, MessageRepository, LogRepository,
    ScorecardRepository, RecycleRepository,
)
from orchestify.migrations.runner import MigrationRunner


@pytest.fixture
def db(tmp_path):
    """Create a fully migrated test database."""
    db_path = tmp_path / "test_repos.db"
    db = DatabaseManager(db_path)
    runner = MigrationRunner(db)
    runner.run_pending()
    return db


# ── Sprint Repository ────────────────────────────────────────────────

class TestSprintRepository:
    def test_create_and_get(self, db):
        repo = SprintRepository(db)
        sprint = SprintRow(sprint_id="test-sprint-1", prompt="Build feature X")
        repo.create(sprint)

        result = repo.get("test-sprint-1")
        assert result is not None
        assert result["sprint_id"] == "test-sprint-1"
        assert result["prompt"] == "Build feature X"
        assert result["status"] == "created"

    def test_get_nonexistent(self, db):
        repo = SprintRepository(db)
        assert repo.get("nonexistent") is None

    def test_get_latest(self, db):
        repo = SprintRepository(db)
        repo.create(SprintRow(sprint_id="old-sprint", created_at="2025-01-01"))
        repo.create(SprintRow(sprint_id="new-sprint", created_at="2025-06-01"))

        latest = repo.get_latest()
        assert latest["sprint_id"] == "new-sprint"

    def test_list_all(self, db):
        repo = SprintRepository(db)
        repo.create(SprintRow(sprint_id="s1"))
        repo.create(SprintRow(sprint_id="s2"))
        repo.create(SprintRow(sprint_id="s3"))

        all_sprints = repo.list_all()
        assert len(all_sprints) == 3

    def test_list_by_status(self, db):
        repo = SprintRepository(db)
        repo.create(SprintRow(sprint_id="s1", status="created"))
        repo.create(SprintRow(sprint_id="s2", status="running"))

        created = repo.list_all(status="created")
        assert len(created) == 1
        assert created[0]["sprint_id"] == "s1"

    def test_update_status(self, db):
        repo = SprintRepository(db)
        repo.create(SprintRow(sprint_id="s1"))
        repo.update_status("s1", "running", pid=12345)

        result = repo.get("s1")
        assert result["status"] == "running"
        assert result["pid"] == 12345
        assert result["started_at"] is not None

    def test_update_progress(self, db):
        repo = SprintRepository(db)
        repo.create(SprintRow(sprint_id="s1"))
        repo.update_progress("s1", 10, 5)

        result = repo.get("s1")
        assert result["issues_total"] == 10
        assert result["issues_done"] == 5


# ── Issue Repository ─────────────────────────────────────────────────

class TestIssueRepository:
    def test_create_and_get(self, db):
        EpicRepository(db).create(EpicRow(epic_id="epic-1"))
        repo = IssueRepository(db)
        issue = IssueRow(issue_number=1, epic_id="epic-1", status="in_progress")
        issue_id = repo.create(issue)

        result = repo.get(issue_id)
        assert result is not None
        assert result["issue_number"] == 1
        assert result["status"] == "in_progress"

    def test_get_by_number(self, db):
        EpicRepository(db).create(EpicRow(epic_id="epic-1"))
        repo = IssueRepository(db)
        repo.create(IssueRow(issue_number=42, epic_id="epic-1"))

        result = repo.get_by_number(42, "epic-1")
        assert result is not None
        assert result["issue_number"] == 42

    def test_list_by_sprint(self, db):
        SprintRepository(db).create(SprintRow(sprint_id="sprint-1"))
        EpicRepository(db).create(EpicRow(epic_id="epic-1", sprint_id="sprint-1"))
        repo = IssueRepository(db)
        repo.create(IssueRow(issue_number=1, epic_id="epic-1", sprint_id="sprint-1"))
        repo.create(IssueRow(issue_number=2, epic_id="epic-1", sprint_id="sprint-1"))

        issues = repo.list_by_sprint("sprint-1")
        assert len(issues) == 2

    def test_increment_cycles(self, db):
        EpicRepository(db).create(EpicRow(epic_id="epic-1"))
        repo = IssueRepository(db)
        issue_id = repo.create(IssueRow(issue_number=1, epic_id="epic-1"))

        repo.increment_cycles(issue_id, "review_cycles")
        repo.increment_cycles(issue_id, "review_cycles")

        result = repo.get(issue_id)
        assert result["review_cycles"] == 2


# ── Message Repository ───────────────────────────────────────────────

class TestMessageRepository:
    def test_create_and_get_by_agent(self, db):
        SprintRepository(db).create(SprintRow(sprint_id="sprint-1"))
        repo = MessageRepository(db)

        msg = AgentMessageRow(
            sprint_id="sprint-1",
            agent_id="engineer",
            message_type="output",
            content="Building module X...",
        )
        repo.create(msg)

        messages = repo.get_by_agent("sprint-1", "engineer")
        assert len(messages) == 1
        assert messages[0]["content"] == "Building module X..."

    def test_batch_create(self, db):
        SprintRepository(db).create(SprintRow(sprint_id="sprint-1"))
        repo = MessageRepository(db)

        msgs = [
            AgentMessageRow(sprint_id="sprint-1", agent_id="eng", message_type="output", content=f"line {i}")
            for i in range(10)
        ]
        count = repo.create_batch(msgs)
        assert count == 10

        messages = repo.get_by_agent("sprint-1", "eng")
        assert len(messages) == 10

    def test_get_by_sprint(self, db):
        SprintRepository(db).create(SprintRow(sprint_id="sprint-1"))
        repo = MessageRepository(db)
        repo.create(AgentMessageRow(sprint_id="sprint-1", agent_id="eng", message_type="output", content="a"))
        repo.create(AgentMessageRow(sprint_id="sprint-1", agent_id="rev", message_type="output", content="b"))

        messages = repo.get_by_sprint("sprint-1")
        assert len(messages) == 2

    def test_count_by_type(self, db):
        SprintRepository(db).create(SprintRow(sprint_id="sprint-1"))
        repo = MessageRepository(db)
        repo.create(AgentMessageRow(sprint_id="sprint-1", agent_id="eng", message_type="output", content="a"))
        repo.create(AgentMessageRow(sprint_id="sprint-1", agent_id="eng", message_type="error", content="b"))
        repo.create(AgentMessageRow(sprint_id="sprint-1", agent_id="eng", message_type="output", content="c"))

        counts = repo.count_by_type("sprint-1")
        assert counts["output"] == 2
        assert counts["error"] == 1


# ── Scorecard Repository ─────────────────────────────────────────────

class TestScorecardRepository:
    def test_create_and_get(self, db):
        EpicRepository(db).create(EpicRow(epic_id="epic-1"))
        IssueRepository(db).create(IssueRow(issue_number=1, epic_id="epic-1"))

        repo = ScorecardRepository(db)
        sc = ScorecardRow(
            issue_id=1, agent_id="engineer",
            scope_control=8, behavior_fidelity=7,
            evidence_orientation=9, actionability=8,
            risk_awareness=7, total=39,
            interpretation="promote",
        )
        repo.create(sc)

        results = repo.get_by_issue(1)
        assert len(results) == 1
        assert results[0]["total"] == 39

    def test_average_scores(self, db):
        EpicRepository(db).create(EpicRow(epic_id="epic-1"))
        IssueRepository(db).create(IssueRow(issue_number=1, epic_id="epic-1"))
        IssueRepository(db).create(IssueRow(issue_number=2, epic_id="epic-1"))

        repo = ScorecardRepository(db)
        repo.create(ScorecardRow(issue_id=1, agent_id="eng", total=40))
        repo.create(ScorecardRow(issue_id=2, agent_id="eng", total=30))

        avg = repo.get_average_scores("eng")
        assert avg["avg_total"] == 35.0
        assert avg["count"] == 2
