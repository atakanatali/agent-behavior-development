"""Abstract base classes for LLM providers.

Defines the interface that all LLM providers must implement and provides
shared data models for communication between providers and orchestification layer.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """Represents a single message in an LLM conversation.

    Attributes:
        role: Message role - one of 'system', 'user', or 'assistant'
        content: Text content of the message
    """

    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider.

    Attributes:
        content: The generated response text
        model: The model identifier used
        tokens_input: Number of input tokens consumed
        tokens_output: Number of output tokens generated
        finish_reason: Reason for completion ('stop', 'max_tokens', 'tool_use', etc.)
        raw_response: Raw response object from the provider (optional)
    """

    content: str
    model: str
    tokens_input: int
    tokens_output: int
    finish_reason: str
    raw_response: Any = None


@dataclass
class TokenUsage:
    """Tracks cumulative token usage and costs.

    Attributes:
        total_input: Total input tokens consumed across all calls
        total_output: Total output tokens generated across all calls
        total_cost_usd: Estimated total cost in USD
        call_count: Number of API calls made
    """

    total_input: int = 0
    total_output: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0

    def reset(self) -> None:
        """Reset all usage metrics to zero."""
        self.total_input = 0
        self.total_output = 0
        self.total_cost_usd = 0.0
        self.call_count = 0


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Defines the interface that all LLM provider implementations must follow,
    including methods for completion and streaming, capability detection,
    and usage tracking.
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        """Initialize the LLM provider.

        Args:
            provider_id: Unique identifier for this provider instance
            config: Configuration dictionary for the provider
        """
        self.provider_id = provider_id
        self.config = config
        self.usage = TokenUsage()
        logger.debug(f"Initialized provider: {provider_id}")

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        tools: list[dict] | None = None,
        thinking: bool = False,
    ) -> LLMResponse:
        """Generate a single completion response.

        Args:
            messages: List of messages in the conversation
            model: Model to use (provider default if None)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool/function definitions (if supported)
            thinking: Enable extended thinking (if supported)

        Returns:
            LLMResponse with the completion result

        Raises:
            ValueError: If parameters are invalid for this provider
            RuntimeError: If API call fails
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion response.

        Yields partial response chunks as they arrive from the API.

        Args:
            messages: List of messages in the conversation
            model: Model to use (provider default if None)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Yields:
            Partial response text chunks

        Raises:
            ValueError: If parameters are invalid for this provider
            RuntimeError: If API call fails
        """
        ...

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return the provider type identifier.

        Returns:
            Type string (e.g., 'anthropic', 'openai', 'litellm')
        """
        ...

    def supports_tools(self) -> bool:
        """Check if this provider supports function/tool calling.

        Returns:
            True if tools are supported, False otherwise
        """
        return False

    def supports_thinking(self) -> bool:
        """Check if this provider supports extended thinking.

        Returns:
            True if extended thinking is supported, False otherwise
        """
        return False

    def supports_code_execution(self) -> bool:
        """Check if this provider supports code execution.

        Returns:
            True if code execution is supported, False otherwise
        """
        return False

    def _track_usage(
        self, input_tokens: int, output_tokens: int, model: str, cost: float = 0.0
    ) -> None:
        """Track token usage and costs for a request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            model: Model identifier
            cost: Estimated cost in USD
        """
        self.usage.total_input += input_tokens
        self.usage.total_output += output_tokens
        self.usage.total_cost_usd += cost
        self.usage.call_count += 1

        logger.debug(
            f"Provider {self.provider_id} usage - Input: {input_tokens}, "
            f"Output: {output_tokens}, Cost: ${cost:.6f}"
        )

    def get_usage(self) -> TokenUsage:
        """Get current token usage statistics.

        Returns:
            TokenUsage object with cumulative metrics
        """
        return self.usage

    def reset_usage(self) -> None:
        """Reset all usage metrics to zero."""
        self.usage.reset()
        logger.debug(f"Reset usage for provider: {self.provider_id}")
