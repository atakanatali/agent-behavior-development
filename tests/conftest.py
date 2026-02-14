"""Shared test fixtures for ABD orchestration engine tests."""
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestify.core.state import (
    CycleState,
    EpicState,
    EpicStatus,
    IssueState,
    IssueStatus,
    StateManager,
)
from orchestify.core.agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Interpretation,
    RecycleOutput,
    Scorecard,
)


@pytest.fixture
def test_db():
    """Create an in-memory database with migrations applied.

    NOTE: Does NOT create a default sprint. Tests that need FK-valid
    sprint_id should use the `sprint_db` or `state_manager` fixture,
    or call `_ensure_sprint(db)` themselves.
    """
    from orchestify.db.database import DatabaseManager
    from orchestify.migrations.runner import MigrationRunner
    db = DatabaseManager(":memory:")
    MigrationRunner(db).run_pending()
    return db


def _ensure_sprint(db, sprint_id="test-sprint"):
    """Helper to ensure a sprint exists in the DB for FK constraints."""
    from orchestify.db.repositories import SprintRepository
    repo = SprintRepository(db)
    if not repo.get(sprint_id):
        from orchestify.db.models import SprintRow
        repo.create(SprintRow(sprint_id=sprint_id, status="created"))


@pytest.fixture
def sprint_db(test_db):
    """Test DB with a default 'test-sprint' already created."""
    _ensure_sprint(test_db)
    return test_db


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary repository root."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    return repo


@pytest.fixture
def state_manager(sprint_db):
    """Create a StateManager with an in-memory DB (sprint pre-created)."""
    return StateManager(sprint_db, sprint_id="test-sprint")


@pytest.fixture
def sample_epic():
    """Create a sample EpicState for testing."""
    return EpicState(
        epic_id="epic-test-001",
        status=EpicStatus.PENDING,
        issues=[
            IssueState(issue_number=1, status=IssueStatus.PENDING),
            IssueState(issue_number=2, status=IssueStatus.PENDING),
            IssueState(issue_number=3, status=IssueStatus.PENDING),
        ],
    )


@pytest.fixture
def sample_context():
    """Create a sample AgentContext."""
    return AgentContext(
        goal="Implement user authentication",
        instructions="Create JWT-based auth with refresh tokens",
        behavior_spec="Follow REST API conventions",
        touches=["src/auth.py", "src/middleware.py"],
        dependencies=["pyjwt", "bcrypt"],
        review_keynotes=["Check token expiry", "Validate input"],
    )


@pytest.fixture
def sample_result():
    """Create a sample AgentResult."""
    return AgentResult(
        output="Implemented JWT auth with refresh tokens",
        files_changed=["src/auth.py", "src/middleware.py"],
        commands_run=["pytest tests/"],
        tokens_used=1500,
        duration=3.5,
    )


@pytest.fixture
def sample_scorecard():
    """Create a sample Scorecard."""
    return Scorecard(
        scope_control=2,
        behavior_fidelity=2,
        evidence_orientation=1,
        actionability=2,
        risk_awareness=1,
    )


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.call = AsyncMock(return_value={
        "content": "Mock LLM response",
        "usage": {"total_tokens": 100},
    })
    return provider


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory with YAML files."""
    config = tmp_path / "config"
    config.mkdir()

    (config / "orchestify.yaml").write_text("""
project:
  name: "Test Project"
  repo: "test/test-repo"
  main_branch: "main"
  branch_prefix: "feature/"

orchestration:
  max_review_cycles: 3
  max_qa_cycles: 3
  auto_merge: true
  sequential_issues: true

issue:
  max_changes_per_issue: 20
  language: "en"
  require_agent_directive: true
  require_done_checklist: true

abd:
  scorecard_enabled: true
  recycle_mandatory: true
  evidence_required: true

dev_loop:
  build_cmd: ""
  lint_cmd: ""
  test_cmd: ""
  max_self_fix: 5
  timeout_per_command: 120
""")

    (config / "agents.yaml").write_text("""
agents:
  tpm:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.7
    thinking: true
    mode: interactive
    max_tokens: 8192
  engineer:
    provider: anthropic
    model: claude-opus-4-6
    temperature: 0.5
    thinking: false
    mode: autonomous
    max_tokens: 8192
""")

    (config / "providers.yaml").write_text("""
providers:
  anthropic:
    type: anthropic
    api_key: test-key-123
    default_model: claude-opus-4-6
    max_tokens: 8192
""")

    return config
