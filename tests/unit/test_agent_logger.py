"""Unit tests for orchestify.core.agent_logger module."""
import json
import pytest
from pathlib import Path

from orchestify.core.agent_logger import AgentLogger


class TestAgentLogger:
    @pytest.fixture
    def logger(self, tmp_path):
        return AgentLogger(tmp_path / "logs")

    def test_log_creates_file(self, logger):
        logger.log("engineer", "started")
        log_file = logger.log_dir / "engineer.log"
        assert log_file.exists()

    def test_log_entry_format(self, logger):
        logger.log("engineer", "code_written", {"files": ["main.py"]})
        entries = logger.get_agent_logs("engineer")
        assert len(entries) == 1
        assert entries[0]["agent_id"] == "engineer"
        assert entries[0]["event"] == "code_written"
        assert entries[0]["data"]["files"] == ["main.py"]
        assert "timestamp" in entries[0]

    def test_log_append_only(self, logger):
        logger.log("engineer", "event_1")
        logger.log("engineer", "event_2")
        logger.log("engineer", "event_3")
        entries = logger.get_agent_logs("engineer")
        assert len(entries) == 3
        events = [e["event"] for e in entries]
        assert events == ["event_1", "event_2", "event_3"]

    def test_log_level(self, logger):
        logger.log("qa", "test_failed", level="ERROR")
        entries = logger.get_agent_logs("qa")
        assert entries[0]["level"] == "ERROR"

    def test_log_context(self, logger):
        logger.log_context("tpm", {
            "goal": "Build auth",
            "instructions": "Use JWT tokens",
            "touches": ["auth.py"],
            "dependencies": ["pyjwt"],
        })
        entries = logger.get_agent_logs("tpm")
        assert entries[0]["event"] == "context_received"
        assert entries[0]["data"]["goal"] == "Build auth"

    def test_log_result(self, logger):
        logger.log_result("engineer", {
            "files_changed": ["auth.py", "middleware.py"],
            "tokens_used": 1500,
            "duration": 3.5,
            "output": "Implemented JWT auth",
        })
        entries = logger.get_agent_logs("engineer")
        assert entries[0]["event"] == "execution_complete"
        assert entries[0]["data"]["tokens_used"] == 1500

    def test_log_scorecard(self, logger):
        logger.log_scorecard("scorecardist", {
            "scope_control": 2,
            "behavior_fidelity": 2,
            "total": 8,
        })
        entries = logger.get_agent_logs("scorecardist")
        assert entries[0]["event"] == "scorecard_evaluated"

    def test_save_and_load_checkpoint(self, logger):
        logger.save_task_checkpoint("engineer", {
            "phase": "implementation",
            "issue_number": 1,
            "progress": 50,
        })
        checkpoint = logger.load_task_checkpoint("engineer")
        assert checkpoint is not None
        assert checkpoint["phase"] == "implementation"
        assert checkpoint["issue_number"] == 1
        assert "updated_at" in checkpoint

    def test_load_nonexistent_checkpoint(self, logger):
        assert logger.load_task_checkpoint("nonexistent") is None

    def test_get_agent_logs_limit(self, logger):
        for i in range(20):
            logger.log("engineer", f"event_{i}")
        entries = logger.get_agent_logs("engineer", limit=5)
        assert len(entries) == 5
        # Should be last 5
        assert entries[-1]["event"] == "event_19"

    def test_get_agent_logs_level_filter(self, logger):
        logger.log("qa", "pass", level="INFO")
        logger.log("qa", "fail", level="ERROR")
        logger.log("qa", "warn", level="WARN")

        errors = logger.get_agent_logs("qa", level="ERROR")
        assert len(errors) == 1
        assert errors[0]["event"] == "fail"

    def test_get_all_agent_ids(self, logger):
        logger.log("engineer", "start")
        logger.log("reviewer", "start")
        logger.log("qa", "start")
        ids = logger.get_all_agent_ids()
        assert set(ids) == {"engineer", "reviewer", "qa"}

    def test_get_timeline(self, logger):
        logger.log("engineer", "code_written")
        logger.log("reviewer", "review_started")
        logger.log("qa", "tests_run")

        timeline = logger.get_timeline(limit=10)
        assert len(timeline) == 3
        # Most recent first
        agent_ids = [e["agent_id"] for e in timeline]
        assert "qa" in agent_ids

    def test_empty_logs(self, logger):
        entries = logger.get_agent_logs("nonexistent")
        assert entries == []

    def test_empty_timeline(self, logger):
        timeline = logger.get_timeline()
        assert timeline == []
