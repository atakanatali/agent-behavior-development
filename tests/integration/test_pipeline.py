"""Integration tests for the full orchestration pipeline."""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestify.core.state import (
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
    Scorecard,
    RecycleOutput,
)
from orchestify.core.engine import OrchestrifyEngine


# ─── Mock Agent for Testing ───


class MockAgent(BaseAgent):
    """Mock agent for integration testing."""

    def __init__(self, agent_id, config=None, provider=None, output="Mock output"):
        self.agent_id = agent_id
        self.config = config or {}
        self.provider = provider
        self.memory_client = None
        self.persona_prompt = "Mock persona"
        self.guardrails = ""
        self._mock_output = output
        self.call_count = 0

    async def execute(self, context):
        self.call_count += 1
        return AgentResult(
            output=self._mock_output,
            files_changed=["mock_file.py"],
            tokens_used=100,
            duration=0.5,
        )

    def score(self, result):
        return Scorecard(
            scope_control=2,
            behavior_fidelity=2,
            evidence_orientation=2,
            actionability=2,
            risk_awareness=0,
        )

    def recycle(self, result, scorecard):
        return RecycleOutput(kept=["mock_pattern"])


# ─── State + Epic Integration ───


class TestStateIntegration:
    def test_full_epic_lifecycle(self, tmp_repo):
        """Test creating and completing an epic with issues."""
        sm = StateManager(tmp_repo)

        # Create epic
        epic = sm.create_epic("epic-integration-001")
        assert epic.status == EpicStatus.PENDING

        # Add issues
        for i in range(1, 4):
            sm.update_issue("epic-integration-001", i, {"status": IssueStatus.PENDING})

        # Process issues
        for i in range(1, 4):
            sm.update_issue(
                "epic-integration-001", i,
                {"status": IssueStatus.IN_PROGRESS, "assigned_agent": "engineer"}
            )
            sm.add_cycle(
                "epic-integration-001", i,
                "engineer", "reviewer", "PR submitted", "OK"
            )
            sm.update_issue(
                "epic-integration-001", i, {"status": IssueStatus.REVIEW}
            )
            sm.add_cycle(
                "epic-integration-001", i,
                "reviewer", "qa", "Approved", "Pass"
            )
            sm.update_issue(
                "epic-integration-001", i, {"status": IssueStatus.QA}
            )
            sm.add_cycle(
                "epic-integration-001", i,
                "qa", "architect", "Tests passed", "Pass"
            )
            sm.update_issue(
                "epic-integration-001", i, {"status": IssueStatus.DONE}
            )

        # Complete epic
        assert sm.is_epic_complete("epic-integration-001") is True
        sm.update_epic_status("epic-integration-001", EpicStatus.COMPLETE)

        # Verify final state
        epic = sm.get_epic("epic-integration-001")
        assert epic.status == EpicStatus.COMPLETE
        assert all(i.status == IssueStatus.DONE for i in epic.issues)

        # Verify cycle history
        for issue in epic.issues:
            assert len(issue.cycle_history) == 3

    def test_state_persistence_across_instances(self, tmp_repo):
        """State should survive across StateManager instances."""
        sm1 = StateManager(tmp_repo)
        sm1.create_epic("persist-test")
        sm1.update_issue("persist-test", 1, {"status": IssueStatus.IN_PROGRESS})
        sm1.add_cycle("persist-test", 1, "engineer", "reviewer", "PR", "OK")

        # New instance reads same state
        sm2 = StateManager(tmp_repo)
        epic = sm2.get_epic("persist-test")
        assert epic is not None
        assert len(epic.issues) == 1
        assert epic.issues[0].status == IssueStatus.IN_PROGRESS
        assert len(epic.issues[0].cycle_history) == 1

    def test_multiple_epics(self, tmp_repo):
        """Multiple epics can coexist."""
        sm = StateManager(tmp_repo)
        sm.create_epic("epic-a")
        sm.create_epic("epic-b")
        sm.update_issue("epic-a", 1, {"status": IssueStatus.DONE})
        sm.update_issue("epic-b", 1, {"status": IssueStatus.PENDING})

        assert sm.is_epic_complete("epic-a") is True
        assert sm.is_epic_complete("epic-b") is False

    def test_issue_escalation_flow(self, tmp_repo):
        """Test the escalation path."""
        sm = StateManager(tmp_repo)
        sm.create_epic("escalation-test")
        sm.update_issue("escalation-test", 1, {"status": IssueStatus.IN_PROGRESS})

        # Simulate 3 failed review cycles
        for i in range(3):
            sm.update_issue("escalation-test", 1, {
                "review_cycles": i + 1,
                "status": IssueStatus.REVIEW,
            })
            sm.add_cycle(
                "escalation-test", 1,
                "reviewer", "engineer",
                f"Review cycle {i + 1}", "Changes requested"
            )

        # Escalate
        sm.update_issue("escalation-test", 1, {"status": IssueStatus.ESCALATED})

        epic = sm.get_epic("escalation-test")
        assert epic.issues[0].status == IssueStatus.ESCALATED
        assert epic.issues[0].review_cycles == 3
        assert len(epic.issues[0].cycle_history) == 3


# ─── Engine Integration Tests (with Mock Agents) ───


class TestEngineIntegration:
    @pytest.fixture
    def engine_setup(self, tmp_repo):
        """Setup engine with mock agents."""
        sm = StateManager(tmp_repo)
        engine = OrchestrifyEngine(
            config={"max_self_fixes": 3},
            state_manager=sm,
            provider_registry={},
            memory_client=None,
        )

        # Register mock agents
        engine.register_agent("tpm", MockAgent("tpm", output="Epic planned"))
        engine.register_agent("architect", MockAgent("architect", output="Architecture done"))
        engine.register_agent("engineer", MockAgent("engineer", output="Code written"))
        engine.register_agent("reviewer", MockAgent("reviewer", output="Looks good, approve"))
        engine.register_agent("qa", MockAgent("qa", output="All tests passed"))

        return engine, sm

    def test_engine_registers_agents(self, engine_setup):
        engine, _ = engine_setup
        assert "tpm" in engine.agents
        assert "architect" in engine.agents
        assert "engineer" in engine.agents
        assert "reviewer" in engine.agents
        assert "qa" in engine.agents

    def test_mock_agent_execution(self):
        agent = MockAgent("test", output="Hello from mock")
        import asyncio
        ctx = AgentContext(goal="Test", instructions="Test", behavior_spec="Test")
        result = asyncio.get_event_loop().run_until_complete(agent.execute(ctx))
        assert result.output == "Hello from mock"
        assert agent.call_count == 1

    def test_mock_agent_scoring(self):
        agent = MockAgent("test")
        result = AgentResult(output="test")
        scorecard = agent.score(result)
        assert scorecard.total == 8
        assert scorecard.interpretation.value == "promote"

    def test_mock_agent_recycle(self):
        agent = MockAgent("test")
        result = AgentResult(output="test")
        scorecard = agent.score(result)
        recycle = agent.recycle(result, scorecard)
        assert recycle.kept == ["mock_pattern"]


# ─── Scorecard + Validation Integration ───


class TestScorecardValidationIntegration:
    def test_scorecard_drives_recycle(self):
        """Scorecard interpretation should drive recycle decisions."""
        # Promote case
        sc_high = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=2, actionability=2, risk_awareness=0,
        )
        assert sc_high.interpretation.value == "promote"

        # Anti-pattern case
        sc_low = Scorecard(
            scope_control=0, behavior_fidelity=0,
            evidence_orientation=1, actionability=1, risk_awareness=0,
        )
        assert sc_low.interpretation.value == "anti-pattern"

    def test_state_stores_scorecard(self, tmp_repo):
        """Scorecards can be stored in issue state."""
        sm = StateManager(tmp_repo)
        sm.create_epic("scorecard-test")
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=1, actionability=2, risk_awareness=1,
        )
        sm.update_issue("scorecard-test", 1, {"scorecard": sc.to_dict()})

        epic = sm.get_epic("scorecard-test")
        stored_sc = epic.issues[0].scorecard
        assert stored_sc["total"] == 8
        assert stored_sc["interpretation"] == "promote"
