"""
Base agent class for ABD orchestration engine.

All agents inherit from BaseAgent and implement the agent execution protocol.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class Interpretation(str, Enum):
    """Scorecard interpretation."""
    PROMOTE = "promote"
    PATCH = "patch"
    ANTI_PATTERN = "anti-pattern"


@dataclass
class AgentContext:
    """Context passed to agent for execution."""
    goal: str
    instructions: str
    behavior_spec: str
    touches: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    review_keynotes: List[str] = field(default_factory=list)
    prior_output: Optional[str] = None
    error_output: Optional[str] = None
    memory_context: Optional[Dict[str, Any]] = None


@dataclass
class AgentResult:
    """Result of agent execution."""
    output: str
    files_changed: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    tokens_used: int = 0
    duration: float = 0.0
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "output": self.output,
            "files_changed": self.files_changed,
            "commands_run": self.commands_run,
            "tokens_used": self.tokens_used,
            "duration": self.duration,
        }


@dataclass
class Scorecard:
    """ABD scorecard for evaluating agent output."""
    scope_control: int  # 0-2: controls changes to necessary scope
    behavior_fidelity: int  # 0-2: follows instructions precisely
    evidence_orientation: int  # 0-2: provides evidence for decisions
    actionability: int  # 0-2: output is actionable
    risk_awareness: int  # 0-2: acknowledges risks and tradeoffs
    total: int = 0
    interpretation: Interpretation = Interpretation.PATCH

    def __post_init__(self):
        """Validate and calculate total."""
        self._validate()
        self.total = (
            self.scope_control
            + self.behavior_fidelity
            + self.evidence_orientation
            + self.actionability
            + self.risk_awareness
        )

        # Auto-interpret
        if self.total >= 8:
            self.interpretation = Interpretation.PROMOTE
        elif self.total <= 3:
            self.interpretation = Interpretation.ANTI_PATTERN
        else:
            self.interpretation = Interpretation.PATCH

    def _validate(self):
        """Validate scorecard values."""
        for field in [
            "scope_control",
            "behavior_fidelity",
            "evidence_orientation",
            "actionability",
            "risk_awareness",
        ]:
            value = getattr(self, field)
            if not isinstance(value, int) or value < 0 or value > 2:
                raise ValueError(f"{field} must be 0-2, got {value}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert scorecard to dictionary."""
        return {
            "scope_control": self.scope_control,
            "behavior_fidelity": self.behavior_fidelity,
            "evidence_orientation": self.evidence_orientation,
            "actionability": self.actionability,
            "risk_awareness": self.risk_awareness,
            "total": self.total,
            "interpretation": self.interpretation.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scorecard":
        """Create scorecard from dictionary."""
        if "total" in data:
            del data["total"]
        if "interpretation" in data and isinstance(data["interpretation"], str):
            data["interpretation"] = Interpretation(data["interpretation"])
        return cls(**data)


@dataclass
class RecycleOutput:
    """Output from agent recycle process."""
    kept: List[str] = field(default_factory=list)
    reused: List[str] = field(default_factory=list)
    banned: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "kept": self.kept,
            "reused": self.reused,
            "banned": self.banned,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecycleOutput":
        """Create from dictionary."""
        return cls(**data)


class BaseAgent(ABC):
    """
    Abstract base class for all ABD agents.

    Agents execute tasks within the orchestration engine and provide scorecards
    for output quality evaluation.
    """

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        provider: Any,
        memory_client: Optional[Any] = None,
    ):
        """
        Initialize agent.

        Args:
            agent_id: Unique agent identifier
            config: Configuration dictionary
            provider: LLM provider instance
            memory_client: Optional memory client for context
        """
        self.agent_id = agent_id
        self.config = config
        self.provider = provider
        self.memory_client = memory_client
        self.persona_prompt = self._load_persona()
        self.guardrails = self._load_guardrails()

    def _load_persona(self) -> str:
        """
        Load persona prompt from file.

        Returns:
            Persona prompt text
        """
        persona_path = Path(__file__).parent.parent / "prompts" / "personas" / f"{self.agent_id}.md"

        if not persona_path.exists():
            raise FileNotFoundError(f"Persona file not found: {persona_path}")

        try:
            with open(persona_path, "r") as f:
                return f.read()
        except IOError as e:
            raise RuntimeError(f"Failed to load persona: {e}")

    def _load_guardrails(self) -> str:
        """
        Load global guardrails.

        Returns:
            Guardrails text
        """
        guardrails_path = Path(__file__).parent.parent / "prompts" / "guardrails.md"

        if not guardrails_path.exists():
            return ""

        try:
            with open(guardrails_path, "r") as f:
                return f.read()
        except IOError:
            return ""

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute agent task.

        Must be implemented by subclasses.

        Args:
            context: Agent execution context

        Returns:
            Agent result
        """
        pass

    def score(self, result: AgentResult) -> Scorecard:
        """
        Score agent output using ABD criteria.

        Should be implemented by subclasses for specific scoring logic.
        Default implementation returns neutral scorecard.

        Args:
            result: Agent result to score

        Returns:
            Scorecard
        """
        return Scorecard(
            scope_control=1,
            behavior_fidelity=1,
            evidence_orientation=1,
            actionability=1,
            risk_awareness=1,
        )

    def recycle(self, result: AgentResult, scorecard: Scorecard) -> RecycleOutput:
        """
        Determine recycling strategy based on result and scorecard.

        Should be implemented by subclasses.
        Default implementation returns empty recycle output.

        Args:
            result: Agent result
            scorecard: Scoring result

        Returns:
            RecycleOutput with kept/reused/banned items
        """
        return RecycleOutput()

    def _build_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """
        Build LLM message array from context.

        Args:
            context: Agent execution context

        Returns:
            List of message dictionaries for LLM
        """
        messages = []

        # System message
        system_parts = [self.persona_prompt]
        if self.guardrails:
            system_parts.append(self.guardrails)

        messages.append({
            "role": "system",
            "content": "\n\n".join(system_parts)
        })

        # Build user message
        user_content_parts = []

        if context.goal:
            user_content_parts.append(f"Goal:\n{context.goal}")

        if context.instructions:
            user_content_parts.append(f"Instructions:\n{context.instructions}")

        if context.behavior_spec:
            user_content_parts.append(f"Behavior Specification:\n{context.behavior_spec}")

        if context.touches:
            user_content_parts.append(f"Files to Touch:\n- " + "\n- ".join(context.touches))

        if context.dependencies:
            user_content_parts.append(f"Dependencies:\n- " + "\n- ".join(context.dependencies))

        if context.review_keynotes:
            user_content_parts.append(f"Review Keynotes:\n- " + "\n- ".join(context.review_keynotes))

        if context.prior_output:
            user_content_parts.append(f"Prior Output:\n{context.prior_output}")

        if context.error_output:
            user_content_parts.append(f"Error to Fix:\n{context.error_output}")

        if context.memory_context:
            memory_str = "\n".join(
                f"{k}: {v}" for k, v in context.memory_context.items()
            )
            user_content_parts.append(f"Memory Context:\n{memory_str}")

        messages.append({
            "role": "user",
            "content": "\n\n".join(user_content_parts)
        })

        return messages

    def _validate_output(self, output: str) -> bool:
        """
        Validate agent output format.

        Should be implemented by subclasses for specific validation.
        Default implementation checks for non-empty output.

        Args:
            output: Agent output text

        Returns:
            True if output is valid
        """
        return bool(output and output.strip())

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int]:
        """
        Call LLM provider.

        Args:
            messages: Message array
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response_text, tokens_used)
        """
        if not hasattr(self.provider, "call"):
            raise NotImplementedError("Provider must implement 'call' method")

        response = await self.provider.call(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or self.config.get("max_tokens", 4096),
        )

        tokens = response.get("usage", {}).get("total_tokens", 0)
        content = response.get("content", "")

        return content, tokens
