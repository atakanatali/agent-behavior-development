"""Unit tests for orchestify.core.sprint module."""
import json
import os
import pytest
from pathlib import Path

from orchestify.core.sprint import (
    Sprint,
    SprintManager,
    generate_sprint_id,
)


class TestGenerateSprintId:
    def test_format(self):
        sid = generate_sprint_id()
        parts = sid.split("-")
        assert len(parts) == 3
        assert parts[0].isalpha()
        assert parts[1].isalpha()
        assert parts[2].isdigit()
        assert len(parts[2]) == 4

    def test_uniqueness(self):
        ids = {generate_sprint_id() for _ in range(50)}
        # With 24*24*9000 combinations, 50 should be unique
        assert len(ids) >= 45


class TestSprint:
    def test_sprint_created(self, test_db):
        sm = SprintManager(test_db)
        sprint = sm.create("test-sprint-001")
        assert sprint.sprint_id == "test-sprint-001"
        assert sprint.exists is True

    def test_sprint_not_exists(self, test_db):
        sm = SprintManager(test_db)
        sprint = sm.get("nonexistent")
        assert sprint is None

    def test_save_and_load_state(self, test_db):
        sm = SprintManager(test_db)
        sprint = sm.create("test-sprint-001")
        state = {"status": "running", "prompt": "Build auth"}
        sprint.save_state(state)

        # Reload and verify
        loaded = sprint.load_state()
        assert loaded["status"] == "running"
        assert loaded["prompt"] == "Build auth"
        # started_at is auto-set by DB when status becomes "running"
        assert loaded["started_at"] is not None

    def test_load_state_default(self, test_db):
        sm = SprintManager(test_db)
        sprint = sm.create("test-sprint-001")
        state = sprint.load_state()
        assert state["status"] == "created"

    def test_to_dict(self, test_db):
        sm = SprintManager(test_db)
        sprint = sm.create("test-sprint-001")
        state = {"status": "running", "started_at": "2025-01-01"}
        sprint.save_state(state)
        d = sprint.to_dict()
        assert d["sprint_id"] == "test-sprint-001"
        assert d["status"] == "running"


class TestSprintManager:
    @pytest.fixture
    def sm(self, test_db):
        return SprintManager(test_db)

    def test_create_sprint(self, sm):
        sprint = sm.create("test-sprint")
        assert sprint.exists
        state = sprint.load_state()
        assert state["sprint_id"] == "test-sprint"
        assert state["status"] == "created"

    def test_create_auto_id(self, sm):
        sprint = sm.create()
        assert sprint.exists
        assert len(sprint.sprint_id.split("-")) == 3

    def test_create_with_prompt(self, sm):
        sprint = sm.create(prompt="Build auth system")
        state = sprint.load_state()
        assert state["prompt"] == "Build auth system"

    def test_get_sprint(self, sm):
        sm.create("find-me")
        found = sm.get("find-me")
        assert found is not None
        assert found.sprint_id == "find-me"

    def test_get_nonexistent(self, sm):
        assert sm.get("nonexistent") is None

    def test_list_sprints(self, sm):
        sm.create("sprint-a")
        sm.create("sprint-b")
        sprints = sm.list_sprints()
        ids = [s.sprint_id for s in sprints]
        assert "sprint-a" in ids
        assert "sprint-b" in ids

    def test_list_empty(self, sm):
        assert sm.list_sprints() == []

    def test_get_latest(self, sm):
        sm.create("first")
        sm.create("second")
        latest = sm.get_latest_sprint()
        assert latest is not None
        assert latest.sprint_id in ("first", "second")

    def test_pause_and_resume(self, sm):
        sprint = sm.create("pausable")
        # Manually set to running
        state = sprint.load_state()
        state["status"] = "running"
        state["pid"] = os.getpid()
        sprint.save_state(state)

        assert sm.pause("pausable") is True
        state = sprint.load_state()
        assert state["status"] == "paused"

        assert sm.resume("pausable") is True
        state = sprint.load_state()
        assert state["status"] == "running"

    def test_pause_non_running(self, sm):
        sm.create("created-only")
        assert sm.pause("created-only") is False

    def test_complete(self, sm):
        sprint = sm.create("completable")
        assert sm.complete("completable") is True
        state = sprint.load_state()
        assert state["status"] == "completed"
        assert state["completed_at"] is not None

    def test_artifacts_dir_created(self, sm):
        sprint = sm.create("full-struct")
        # Artifacts directory should exist
        assert sprint.artifacts_dir.exists()
