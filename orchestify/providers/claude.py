"""Anthropic Claude LLM provider implementation.

Provides integration with Anthropic's Claude models via the official Python SDK.
Supports tool use, extended thinking, and other Claude-specific features.
"""

import json
import logging
import os
import re
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic, APIError, RateLimitError, APIConnectionError
try:
    from anthropic.types.message import ContentBlock, ToolUseBlock, TextBlock
except ImportError:
    from anthropic.types import ContentBlock, TextBlock
    try:
        from anthropic.types import ToolUseBlock
    except ImportError:
        ToolUseBlock = None

from orchestify.providers.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Approximate pricing for Claude models (as of knowledge cutoff)
# Input pricing per 1M tokens, Output pricing per 1M tokens
CLAUDE_PRICING = {
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.80, "output": 4.00},
}

# Models that support extended thinking
THINKING_CAPABLE_MODELS = {
    "claude-3-7-sonnet-20250219",
}


class ClaudeProvider(LLMProvider):
    """Anthropic Claude LLM provider.

    Supports:
    - Single completions and streaming
    - Tool/function calling
    - Extended thinking (for compatible models)
    - Batch processing
    - Vision capabilities (with image content)
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        """Initialize Claude provider.

        Args:
            provider_id: Unique identifier for this provider instance
            config: Configuration dict with:
                - api_key: Anthropic API key (supports ${ENV_VAR} substitution)
                - default_model: Default model to use
                - max_tokens: Maximum tokens per request
                - base_url: Optional custom API endpoint

        Raises:
            ValueError: If api_key is missing or invalid
        """
        super().__init__(provider_id, config)

        # Resolve API key with environment variable substitution
        api_key = config.get("api_key", "")
        if not api_key:
            raise ValueError(f"Provider {provider_id}: api_key is required")

        api_key = self._resolve_env_var(api_key)
        if not api_key:
            raise ValueError(f"Provider {provider_id}: api_key could not be resolved")

        # Initialize Anthropic client
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if "base_url" in config and config["base_url"]:
            client_kwargs["base_url"] = config["base_url"]

        self.client = AsyncAnthropic(**client_kwargs)
        self.default_model = config.get("default_model", "claude-3-5-sonnet")
        self.max_tokens = config.get("max_tokens", 8192)

        logger.info(
            f"Initialized Claude provider {provider_id} with model {self.default_model}"
        )

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """Resolve environment variable substitution in format ${VAR_NAME}.

        Args:
            value: String that may contain ${VAR_NAME} patterns

        Returns:
            String with environment variables substituted
        """
        pattern = r"\$\{([^}]+)\}"

        def replace_env(match: Any) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return re.sub(pattern, replace_env, value)

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        tools: list[dict] | None = None,
        thinking: bool = False,
    ) -> LLMResponse:
        """Generate a single completion using Claude.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default_model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool definitions for function calling
            thinking: Enable extended thinking if supported

        Returns:
            LLMResponse with the completion result

        Raises:
            ValueError: If model is not a valid Claude model
            RateLimitError: If rate limit is exceeded
            APIError: If API call fails
        """
        model = model or self.default_model
        self._validate_model(model)

        # Enforce max tokens limit
        max_tokens = min(max_tokens, self.max_tokens)

        # Convert messages to Anthropic format
        anthropic_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            # Build request kwargs
            request_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": anthropic_messages,
            }

            # Add tools if provided and supported
            if tools and self.supports_tools():
                request_kwargs["tools"] = tools

            # Add extended thinking if requested and supported
            if thinking and self.supports_thinking():
                request_kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": min(max_tokens // 2, 10000),
                }

            # Make API call
            response = await self.client.messages.create(**request_kwargs)

            # Extract content
            content = self._extract_content(response.content)

            # Track usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            self._track_usage(input_tokens, output_tokens, model, cost)

            logger.debug(
                f"Claude completion - Model: {model}, Tokens in: {input_tokens}, "
                f"out: {output_tokens}, Cost: ${cost:.6f}"
            )

            return LLMResponse(
                content=content,
                model=model,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                finish_reason=response.stop_reason,
                raw_response=response,
            )

        except RateLimitError as e:
            logger.error(f"Claude rate limit exceeded: {e}")
            raise
        except APIConnectionError as e:
            logger.error(f"Claude API connection error: {e}")
            raise
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion using Claude.

        Yields partial response chunks as they arrive from the API.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default_model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Yields:
            Partial response text chunks

        Raises:
            ValueError: If model is not a valid Claude model
            APIError: If API call fails
        """
        model = model or self.default_model
        self._validate_model(model)

        # Enforce max tokens limit
        max_tokens = min(max_tokens, self.max_tokens)

        # Convert messages to Anthropic format
        anthropic_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=anthropic_messages,
            ) as stream:
                input_tokens = 0
                output_tokens = 0

                async for event in stream:
                    # Handle content block delta events
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield event.delta.text
                    # Track final usage
                    elif event.type == "message_delta":
                        if hasattr(event, "usage"):
                            output_tokens = event.usage.output_tokens

                    # Get input tokens from initial message start
                    elif event.type == "message_start":
                        if hasattr(event.message, "usage"):
                            input_tokens = event.message.usage.input_tokens

                # Track usage
                if input_tokens > 0 or output_tokens > 0:
                    cost = self._calculate_cost(model, input_tokens, output_tokens)
                    self._track_usage(input_tokens, output_tokens, model, cost)

        except APIError as e:
            logger.error(f"Claude streaming API error: {e}")
            raise

    @property
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            'anthropic'
        """
        return "anthropic"

    def supports_tools(self) -> bool:
        """Check if this provider supports function/tool calling.

        Returns:
            True (Claude supports tool use)
        """
        return True

    def supports_thinking(self) -> bool:
        """Check if this provider supports extended thinking.

        Returns:
            True if the configured model supports thinking, False otherwise
        """
        return self.default_model in THINKING_CAPABLE_MODELS

    def supports_code_execution(self) -> bool:
        """Check if this provider supports code execution.

        Returns:
            False (Claude does not have direct code execution)
        """
        return False

    @staticmethod
    def _validate_model(model: str) -> None:
        """Validate that the model string is a valid Claude model.

        Args:
            model: Model identifier to validate

        Raises:
            ValueError: If model is not recognized as a Claude model
        """
        if not model.startswith("claude-"):
            raise ValueError(
                f"Invalid Claude model: {model}. Model must start with 'claude-'"
            )

    @staticmethod
    def _extract_content(content_blocks: list[ContentBlock]) -> str:
        """Extract text content from Anthropic message content blocks.

        Handles text blocks and tool use blocks.

        Args:
            content_blocks: List of content blocks from API response

        Returns:
            Extracted text content
        """
        text_parts = []

        for block in content_blocks:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                # Include tool use information
                text_parts.append(
                    f"[Tool Use: {block.name}]\n{json.dumps(block.input, indent=2)}"
                )

        return "\n".join(text_parts)

    @staticmethod
    def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate approximate cost for a completion.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Extract base model name for pricing lookup
        base_model = model
        for known_model in CLAUDE_PRICING:
            if model.startswith(known_model):
                base_model = known_model
                break

        pricing = CLAUDE_PRICING.get(base_model, {"input": 3.00, "output": 15.00})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
