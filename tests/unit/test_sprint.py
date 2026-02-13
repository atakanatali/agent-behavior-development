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
    @pytest.fixture
    def sprint_dir(self, tmp_path):
        d = tmp_path / "test-sprint-001"
        d.mkdir()
        return d

    def test_exists(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        assert sprint.exists is True

    def test_not_exists(self, tmp_path):
        sprint = Sprint(tmp_path / "nonexistent")
        assert sprint.exists is False

    def test_sprint_id(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        assert sprint.sprint_id == "test-sprint-001"

    def test_save_and_load_state(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        state = {"status": "running", "started_at": "2025-01-01T00:00:00"}
        sprint.save_state(state)

        loaded = sprint.load_state()
        assert loaded["status"] == "running"
        assert loaded["started_at"] == "2025-01-01T00:00:00"

    def test_load_state_default(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        state = sprint.load_state()
        assert state["status"] == "created"

    def test_log_file(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        log_file = sprint.get_log_file("engineer")
        assert log_file.parent.name == "logs"
        assert log_file.name == "engineer.log"

    def test_task_file(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        task_file = sprint.get_task_file("engineer")
        assert task_file.name == "engineer_task.yaml"

    def test_to_dict(self, sprint_dir):
        sprint = Sprint(sprint_dir)
        sprint.save_state({"status": "running", "started_at": "2025-01-01"})
        d = sprint.to_dict()
        assert d["sprint_id"] == "test-sprint-001"
        assert d["status"] == "running"


class TestSprintManager:
    @pytest.fixture
    def repo_root(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        return repo

    @pytest.fixture
    def sm(self, repo_root):
        return SprintManager(repo_root)

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
        # Should be the last alphabetically since we sort by directory name
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
        assert state["status"] == "complete"
        assert state["completed_at"] is not None

    def test_update_gitignore(self, sm, repo_root):
        gitignore = repo_root / ".gitignore"
        gitignore.write_text("node_modules/\n")
        sm.update_gitignore()

        content = gitignore.read_text()
        assert ".orchestify/*/logs/" in content
        assert ".orchestify/*/state.json" in content
        assert "node_modules/" in content

    def test_update_gitignore_idempotent(self, sm, repo_root):
        gitignore = repo_root / ".gitignore"
        sm.update_gitignore()
        sm.update_gitignore()  # Second call should not duplicate

        content = gitignore.read_text()
        assert content.count(".orchestify/*/logs/") == 1

    def test_sprint_directory_structure(self, sm):
        sprint = sm.create("full-struct")
        assert (sprint.sprint_dir / "logs").exists()
        assert (sprint.sprint_dir / "artifacts").exists()
        assert (sprint.sprint_dir / "personas").exists()
        assert (sprint.sprint_dir / "rules").exists()
        assert (sprint.sprint_dir / "prompts").exists()
        assert (sprint.sprint_dir / "config.yaml").exists()
        assert (sprint.sprint_dir / "state.json").exists()
