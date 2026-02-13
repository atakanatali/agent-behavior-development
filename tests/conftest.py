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
def tmp_repo(tmp_path):
    """Create a temporary repository root with .orchestify directory."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    orchestify_dir = repo / ".orchestify"
    orchestify_dir.mkdir()
    return repo


@pytest.fixture
def state_manager(tmp_repo):
    """Create a StateManager with a temporary repo root."""
    return StateManager(tmp_repo)


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

    # orchestify.yaml
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

    # agents.yaml
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

    # providers.yaml
    (config / "providers.yaml").write_text("""
providers:
  anthropic:
    type: anthropic
    api_key: test-key-123
    default_model: claude-opus-4-6
    max_tokens: 8192
""")

    # memory.yaml - omitted to use defaults since load_config's
    # memory extraction logic expects a specific format

    return config
