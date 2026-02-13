"""Tests for orchestify.db.console — AgentConsoleReader and ConsoleWriter."""
import time
import threading
from pathlib import Path

import pytest

from orchestify.db.database import DatabaseManager
from orchestify.db.models import AgentMessageRow, SprintRow
from orchestify.db.repositories import MessageRepository, SprintRepository
from orchestify.db.console import AgentConsoleReader, ConsoleWriter
from orchestify.migrations.runner import MigrationRunner


@pytest.fixture
def db(tmp_path):
    """Create a fully migrated test database."""
    db_path = tmp_path / "test_console.db"
    db = DatabaseManager(db_path)
    runner = MigrationRunner(db)
    runner.run_pending()
    # Create a sprint for FK
    SprintRepository(db).create(SprintRow(sprint_id="test-sprint"))
    return db


class TestAgentConsoleReader:
    """Tests for AgentConsoleReader."""

    def test_get_history_empty(self, db):
        """Should return empty list when no messages exist."""
        reader = AgentConsoleReader(db, "test-sprint", "engineer")
        history = reader.get_history()
        assert history == []

    def test_get_history(self, db):
        """Should return historical messages."""
        repo = MessageRepository(db)
        for i in range(5):
            repo.create(AgentMessageRow(
                sprint_id="test-sprint",
                agent_id="engineer",
                message_type="output",
                content=f"line {i}",
            ))

        reader = AgentConsoleReader(db, "test-sprint", "engineer")
        history = reader.get_history()
        assert len(history) == 5

    def test_get_history_filtered(self, db):
        """Should filter by message type."""
        repo = MessageRepository(db)
        repo.create(AgentMessageRow(
            sprint_id="test-sprint", agent_id="engineer",
            message_type="output", content="out",
        ))
        repo.create(AgentMessageRow(
            sprint_id="test-sprint", agent_id="engineer",
            message_type="error", content="err",
        ))

        reader = AgentConsoleReader(db, "test-sprint", "engineer")
        errors = reader.get_history(message_type="error")
        assert len(errors) == 1
        assert errors[0]["content"] == "err"

    def test_get_history_all_agents(self, db):
        """Should return messages from all agents when agent_id is None."""
        repo = MessageRepository(db)
        repo.create(AgentMessageRow(
            sprint_id="test-sprint", agent_id="engineer",
            message_type="output", content="eng msg",
        ))
        repo.create(AgentMessageRow(
            sprint_id="test-sprint", agent_id="reviewer",
            message_type="output", content="rev msg",
        ))

        reader = AgentConsoleReader(db, "test-sprint", agent_id=None)
        history = reader.get_history()
        assert len(history) == 2

    def test_stop(self, db):
        """Should stop tailing."""
        reader = AgentConsoleReader(db, "test-sprint", "engineer")
        reader.stop()
        assert reader._stop_event.is_set()


class TestConsoleWriter:
    """Tests for ConsoleWriter."""

    def test_write_and_flush(self, db):
        """Should write messages to DB after flush."""
        writer = ConsoleWriter(db, "test-sprint", "engineer")

        writer.write("hello world", message_type="output")
        writer.write("second line", message_type="output")

        # Force flush
        writer._flush_now()

        repo = MessageRepository(db)
        messages = repo.get_by_agent("test-sprint", "engineer")
        assert len(messages) == 2
        assert messages[0]["content"] == "hello world"

    def test_batch_flush(self, db):
        """Should auto-flush when batch size is reached."""
        writer = ConsoleWriter(db, "test-sprint", "engineer")
        writer.BATCH_SIZE = 5

        for i in range(6):
            writer.write(f"msg {i}")

        # First 5 should have been auto-flushed, 1 in buffer
        repo = MessageRepository(db)
        messages = repo.get_by_agent("test-sprint", "engineer")
        assert len(messages) == 5

        # Flush remaining
        writer._flush_now()
        messages = repo.get_by_agent("test-sprint", "engineer")
        assert len(messages) == 6

    def test_start_stop(self, db):
        """Should start and stop the background flush thread."""
        writer = ConsoleWriter(db, "test-sprint", "engineer")
        writer.FLUSH_INTERVAL = 0.05

        writer.start()
        writer.write("background msg")
        time.sleep(0.3)  # Wait for flush
        writer.stop()

        repo = MessageRepository(db)
        messages = repo.get_by_agent("test-sprint", "engineer")
        assert len(messages) >= 1

    def test_stop_flushes_remaining(self, db):
        """Should flush remaining buffer on stop."""
        writer = ConsoleWriter(db, "test-sprint", "engineer")
        writer.write("final msg")
        writer.stop()

        repo = MessageRepository(db)
        messages = repo.get_by_agent("test-sprint", "engineer")
        assert len(messages) == 1

    def test_write_with_metadata(self, db):
        """Should write messages with metadata."""
        writer = ConsoleWriter(db, "test-sprint", "engineer")
        writer.write(
            "review feedback",
            message_type="communication",
            related_agent="reviewer",
            metadata='{"type": "review"}',
        )
        writer._flush_now()

        repo = MessageRepository(db)
        messages = repo.get_by_agent("test-sprint", "engineer")
        assert len(messages) == 1
        assert messages[0]["message_type"] == "communication"
        assert messages[0]["related_agent"] == "reviewer"
