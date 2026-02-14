"""
Agent console reader for orchestify.

Provides tail-like streaming of agent messages from the database,
enabling live console attach and history replay.
"""
import time
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional

from orchestify.db.database import DatabaseManager
from orchestify.db.repositories import MessageRepository


class AgentConsoleReader:
    """
    Tail-like reader for agent console output.

    Polls the agent_messages table at a configurable interval and
    yields new messages. Supports:
    - Live tail (--follow mode)
    - History replay from a timestamp
    - Filtering by message type and level
    - Callback-based streaming for UI integration
    """

    DEFAULT_POLL_INTERVAL = 0.1  # 100ms

    def __init__(
        self,
        db: DatabaseManager,
        sprint_id: str,
        agent_id: Optional[str] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ):
        self.db = db
        self.sprint_id = sprint_id
        self.agent_id = agent_id
        self.poll_interval = poll_interval
        self._repo = MessageRepository(db)
        self._stop_event = threading.Event()
        self._last_timestamp: Optional[str] = None
        self._last_id: int = 0

    def get_history(
        self,
        limit: int = 200,
        since: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get historical messages (non-streaming).

        Args:
            limit: Maximum number of messages to return
            since: ISO timestamp to start from
            message_type: Filter by type (log, output, error, etc.)

        Returns:
            List of message dicts ordered by timestamp
        """
        if self.agent_id:
            return self._repo.get_by_agent(
                sprint_id=self.sprint_id,
                agent_id=self.agent_id,
                since=since,
                limit=limit,
                message_type=message_type,
            )
        else:
            return self._repo.get_by_sprint(
                sprint_id=self.sprint_id,
                since=since,
                limit=limit,
            )

    def tail(
        self,
        callback: Callable[[Dict], None],
        history_lines: int = 50,
        message_type: Optional[str] = None,
    ) -> None:
        """
        Start tailing messages (blocking).

        First replays recent history, then polls for new messages.
        Call stop() from another thread to terminate.

        Args:
            callback: Function called with each new message dict
            history_lines: Number of historical lines to show first
            message_type: Filter by message type
        """
        # Show recent history first
        history = self.get_history(limit=history_lines, message_type=message_type)
        for msg in history:
            callback(msg)
            self._update_cursor(msg)

        # Poll for new messages
        while not self._stop_event.is_set():
            new_messages = self._poll(message_type=message_type)
            for msg in new_messages:
                callback(msg)
                self._update_cursor(msg)

            self._stop_event.wait(self.poll_interval)

    def tail_async(
        self,
        callback: Callable[[Dict], None],
        history_lines: int = 50,
        message_type: Optional[str] = None,
    ) -> threading.Thread:
        """
        Start tailing in a background thread.

        Returns the thread handle. Call stop() to terminate.
        """
        thread = threading.Thread(
            target=self.tail,
            args=(callback, history_lines, message_type),
            daemon=True,
            name=f"console-{self.agent_id or 'all'}",
        )
        thread.start()
        return thread

    def stop(self) -> None:
        """Signal the tail loop to stop."""
        self._stop_event.set()

    def _poll(self, message_type: Optional[str] = None) -> List[Dict]:
        """Poll for messages newer than the cursor."""
        if self.agent_id:
            messages = self._repo.get_by_agent(
                sprint_id=self.sprint_id,
                agent_id=self.agent_id,
                since=self._last_timestamp,
                limit=100,
                message_type=message_type,
            )
        else:
            messages = self._repo.get_by_sprint(
                sprint_id=self.sprint_id,
                since=self._last_timestamp,
                limit=100,
            )

        # Filter out already-seen messages (by id to avoid duplicates)
        return [m for m in messages if m.get("id", 0) > self._last_id]

    def _update_cursor(self, msg: Dict) -> None:
        """Update the read cursor after processing a message."""
        self._last_timestamp = msg.get("timestamp", self._last_timestamp)
        msg_id = msg.get("id", 0)
        if msg_id > self._last_id:
            self._last_id = msg_id


class ConsoleWriter:
    """
    Async writer for agent console output.

    Buffers messages and flushes to DB in batches
    to avoid blocking the pipeline thread.
    """

    FLUSH_INTERVAL = 0.5   # 500ms
    BATCH_SIZE = 50

    def __init__(self, db: DatabaseManager, sprint_id: str, agent_id: str):
        self.db = db
        self.sprint_id = sprint_id
        self.agent_id = agent_id
        self._repo = MessageRepository(db)
        self._buffer: List = []
        self._lock = threading.RLock()
        self._flush_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def write(
        self,
        content: str,
        message_type: str = "output",
        level: str = "INFO",
        epic_id: Optional[str] = None,
        issue_id: Optional[int] = None,
        related_agent: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> None:
        """
        Buffer a message for async DB write.

        The message is immediately available for streaming readers
        after the next flush cycle.
        """
        from orchestify.db.models import AgentMessageRow

        msg = AgentMessageRow(
            sprint_id=self.sprint_id,
            agent_id=self.agent_id,
            message_type=message_type,
            content=content,
            epic_id=epic_id,
            issue_id=issue_id,
            level=level,
            related_agent=related_agent,
            metadata=metadata,
        )

        with self._lock:
            self._buffer.append(msg)
            if len(self._buffer) >= self.BATCH_SIZE:
                self._flush_now()

    def start(self) -> None:
        """Start the background flush thread."""
        self._stop_event.clear()
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name=f"console-writer-{self.agent_id}",
        )
        self._flush_thread.start()

    def stop(self) -> None:
        """Stop the flush thread and flush remaining buffer."""
        self._stop_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=2.0)
        self._flush_now()  # Final flush

    def _flush_loop(self) -> None:
        """Background loop that flushes buffer periodically."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.FLUSH_INTERVAL)
            self._flush_now()

    def _flush_now(self) -> None:
        """Flush current buffer to database."""
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer.clear()

        try:
            self._repo.create_batch(batch)
        except Exception:
            # Re-add to buffer on failure (best effort)
            with self._lock:
                self._buffer = batch + self._buffer
