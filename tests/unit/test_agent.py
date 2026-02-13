"""Unit tests for orchestify.core.agent module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from orchestify.core.agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Interpretation,
    RecycleOutput,
    Scorecard,
)


# ─── Scorecard Tests ───


class TestScorecard:
    def test_create_valid_scorecard(self):
        sc = Scorecard(
            scope_control=2,
            behavior_fidelity=2,
            evidence_orientation=1,
            actionability=2,
            risk_awareness=1,
        )
        assert sc.total == 8
        assert sc.interpretation == Interpretation.PROMOTE

    def test_promote_interpretation(self):
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=2, actionability=2, risk_awareness=0,
        )
        assert sc.total == 8
        assert sc.interpretation == Interpretation.PROMOTE

    def test_patch_interpretation(self):
        sc = Scorecard(
            scope_control=1, behavior_fidelity=1,
            evidence_orientation=1, actionability=1, risk_awareness=1,
        )
        assert sc.total == 5
        assert sc.interpretation == Interpretation.PATCH

    def test_anti_pattern_interpretation(self):
        sc = Scorecard(
            scope_control=0, behavior_fidelity=1,
            evidence_orientation=0, actionability=1, risk_awareness=1,
        )
        assert sc.total == 3
        assert sc.interpretation == Interpretation.ANTI_PATTERN

    def test_max_score(self):
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=2, actionability=2, risk_awareness=2,
        )
        assert sc.total == 10
        assert sc.interpretation == Interpretation.PROMOTE

    def test_min_score(self):
        sc = Scorecard(
            scope_control=0, behavior_fidelity=0,
            evidence_orientation=0, actionability=0, risk_awareness=0,
        )
        assert sc.total == 0
        assert sc.interpretation == Interpretation.ANTI_PATTERN

    def test_invalid_score_negative(self):
        with pytest.raises(ValueError, match="must be 0-2"):
            Scorecard(
                scope_control=-1, behavior_fidelity=1,
                evidence_orientation=1, actionability=1, risk_awareness=1,
            )

    def test_invalid_score_too_high(self):
        with pytest.raises(ValueError, match="must be 0-2"):
            Scorecard(
                scope_control=3, behavior_fidelity=1,
                evidence_orientation=1, actionability=1, risk_awareness=1,
            )

    def test_to_dict(self, sample_scorecard):
        d = sample_scorecard.to_dict()
        assert d["scope_control"] == 2
        assert d["total"] == 8
        assert d["interpretation"] == "promote"

    def test_from_dict(self):
        data = {
            "scope_control": 1,
            "behavior_fidelity": 2,
            "evidence_orientation": 1,
            "actionability": 1,
            "risk_awareness": 1,
        }
        sc = Scorecard.from_dict(data)
        assert sc.total == 6
        assert sc.interpretation == Interpretation.PATCH

    def test_from_dict_ignores_total(self):
        data = {
            "scope_control": 2,
            "behavior_fidelity": 2,
            "evidence_orientation": 2,
            "actionability": 2,
            "risk_awareness": 2,
            "total": 999,
            "interpretation": "patch",
        }
        sc = Scorecard.from_dict(data)
        assert sc.total == 10  # Recalculated
        assert sc.interpretation == Interpretation.PROMOTE  # Recalculated

    def test_boundary_promote(self):
        """Score 8 should be promote."""
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=2, actionability=2, risk_awareness=0,
        )
        assert sc.interpretation == Interpretation.PROMOTE

    def test_boundary_patch_upper(self):
        """Score 7 should be patch."""
        sc = Scorecard(
            scope_control=2, behavior_fidelity=2,
            evidence_orientation=1, actionability=1, risk_awareness=1,
        )
        assert sc.total == 7
        assert sc.interpretation == Interpretation.PATCH

    def test_boundary_patch_lower(self):
        """Score 4 should be patch."""
        sc = Scorecard(
            scope_control=1, behavior_fidelity=1,
            evidence_orientation=1, actionability=1, risk_awareness=0,
        )
        assert sc.total == 4
        assert sc.interpretation == Interpretation.PATCH

    def test_boundary_anti_pattern(self):
        """Score 3 should be anti-pattern."""
        sc = Scorecard(
            scope_control=1, behavior_fidelity=1,
            evidence_orientation=1, actionability=0, risk_awareness=0,
        )
        assert sc.total == 3
        assert sc.interpretation == Interpretation.ANTI_PATTERN


# ─── AgentContext Tests ───


class TestAgentContext:
    def test_create_minimal(self):
        ctx = AgentContext(goal="Test", instructions="Do something", behavior_spec="Be good")
        assert ctx.goal == "Test"
        assert ctx.touches == []
        assert ctx.dependencies == []
        assert ctx.prior_output is None

    def test_create_full(self, sample_context):
        assert sample_context.goal == "Implement user authentication"
        assert len(sample_context.touches) == 2
        assert len(sample_context.dependencies) == 2
        assert len(sample_context.review_keynotes) == 2


# ─── AgentResult Tests ───


class TestAgentResult:
    def test_create_minimal(self):
        result = AgentResult(output="Done")
        assert result.output == "Done"
        assert result.files_changed == []
        assert result.tokens_used == 0

    def test_to_dict(self, sample_result):
        d = sample_result.to_dict()
        assert d["output"] == "Implemented JWT auth with refresh tokens"
        assert d["tokens_used"] == 1500
        assert len(d["files_changed"]) == 2


# ─── RecycleOutput Tests ───


class TestRecycleOutput:
    def test_create_default(self):
        ro = RecycleOutput()
        assert ro.kept == []
        assert ro.reused == []
        assert ro.banned == []

    def test_create_with_data(self):
        ro = RecycleOutput(
            kept=["good_pattern"],
            reused=["reusable_module"],
            banned=["bad_practice"],
        )
        assert len(ro.kept) == 1
        assert len(ro.banned) == 1

    def test_to_dict(self):
        ro = RecycleOutput(kept=["a"], reused=["b"], banned=["c"])
        d = ro.to_dict()
        assert d == {"kept": ["a"], "reused": ["b"], "banned": ["c"]}

    def test_from_dict(self):
        data = {"kept": ["x"], "reused": [], "banned": ["y"]}
        ro = RecycleOutput.from_dict(data)
        assert ro.kept == ["x"]
        assert ro.banned == ["y"]


# ─── Interpretation Tests ───


class TestInterpretation:
    def test_values(self):
        assert Interpretation.PROMOTE.value == "promote"
        assert Interpretation.PATCH.value == "patch"
        assert Interpretation.ANTI_PATTERN.value == "anti-pattern"

    def test_from_string(self):
        assert Interpretation("promote") == Interpretation.PROMOTE
        assert Interpretation("anti-pattern") == Interpretation.ANTI_PATTERN


# ─── BaseAgent Tests ───


class TestBaseAgent:
    def test_cannot_instantiate_abstract(self):
        """BaseAgent is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent("test", {}, MagicMock())

    def test_concrete_agent(self, mock_provider):
        """A concrete agent can be created."""
        class ConcreteAgent(BaseAgent):
            def _load_persona(self):
                return "Test persona"

            async def execute(self, context):
                return AgentResult(output="done")

        agent = ConcreteAgent("test", {}, mock_provider)
        assert agent.agent_id == "test"
        assert agent.persona_prompt == "Test persona"

    def test_validate_output_nonempty(self, mock_provider):
        class ConcreteAgent(BaseAgent):
            def _load_persona(self):
                return "Test"

            async def execute(self, context):
                return AgentResult(output="done")

        agent = ConcreteAgent("test", {}, mock_provider)
        assert agent._validate_output("hello") is True
        assert agent._validate_output("") is False
        assert agent._validate_output("   ") is False

    def test_default_score(self, mock_provider):
        class ConcreteAgent(BaseAgent):
            def _load_persona(self):
                return "Test"

            async def execute(self, context):
                return AgentResult(output="done")

        agent = ConcreteAgent("test", {}, mock_provider)
        result = AgentResult(output="test")
        scorecard = agent.score(result)
        assert scorecard.total == 5
        assert scorecard.interpretation == Interpretation.PATCH

    def test_default_recycle(self, mock_provider):
        class ConcreteAgent(BaseAgent):
            def _load_persona(self):
                return "Test"

            async def execute(self, context):
                return AgentResult(output="done")

        agent = ConcreteAgent("test", {}, mock_provider)
        result = AgentResult(output="test")
        scorecard = Scorecard(
            scope_control=1, behavior_fidelity=1,
            evidence_orientation=1, actionability=1, risk_awareness=1,
        )
        recycle = agent.recycle(result, scorecard)
        assert recycle.kept == []
        assert recycle.reused == []
        assert recycle.banned == []

    def test_build_messages(self, mock_provider, sample_context):
        class ConcreteAgent(BaseAgent):
            def _load_persona(self):
                return "You are an engineer"

            def _load_guardrails(self):
                return "Follow standards"

            async def execute(self, context):
                return AgentResult(output="done")

        agent = ConcreteAgent("test", {}, mock_provider)
        messages = agent._build_messages(sample_context)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "You are an engineer" in messages[0]["content"]
        assert "Follow standards" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "Implement user authentication" in messages[1]["content"]
        assert "src/auth.py" in messages[1]["content"]

    def test_build_messages_with_error_output(self, mock_provider):
        class ConcreteAgent(BaseAgent):
            def _load_persona(self):
                return "Engineer"

            def _load_guardrails(self):
                return ""

            async def execute(self, context):
                return AgentResult(output="done")

        agent = ConcreteAgent("test", {}, mock_provider)
        ctx = AgentContext(
            goal="Fix bug",
            instructions="Fix the null pointer",
            behavior_spec="Be careful",
            error_output="NullPointerException at line 42",
        )
        messages = agent._build_messages(ctx)
        assert "NullPointerException" in messages[1]["content"]
        assert "Error to Fix" in messages[1]["content"]
