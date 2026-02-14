"""OpenAI LLM provider implementation.

Provides integration with OpenAI's API including GPT-4, GPT-4 Turbo, and other models.
Supports tool use, streaming, and other OpenAI-specific features.
"""

import json
import logging
import os
import re
from typing import Any, AsyncIterator

from openai import AsyncOpenAI, RateLimitError, APIError

from orchestify.providers.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Approximate pricing for OpenAI models (as of knowledge cutoff)
# Input pricing per 1M tokens, Output pricing per 1M tokens
OPENAI_PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider.

    Supports:
    - Single completions and streaming
    - Tool/function calling (via function_calling)
    - Vision capabilities (with image content)
    - Batch processing via batch API
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        """Initialize OpenAI provider.

        Args:
            provider_id: Unique identifier for this provider instance
            config: Configuration dict with:
                - api_key: OpenAI API key (supports ${ENV_VAR} substitution)
                - default_model: Default model to use
                - max_tokens: Maximum tokens per request
                - base_url: Optional custom API endpoint (for proxies, etc.)

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

        # Initialize OpenAI client
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if "base_url" in config and config["base_url"]:
            client_kwargs["base_url"] = config["base_url"]

        self.client = AsyncOpenAI(**client_kwargs)
        self.default_model = config.get("default_model", "gpt-4o")
        self.max_tokens = config.get("max_tokens", 8192)

        logger.info(
            f"Initialized OpenAI provider {provider_id} with model {self.default_model}"
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
        """Generate a single completion using OpenAI.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default_model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool/function definitions for function calling
            thinking: Extended thinking (ignored for OpenAI)

        Returns:
            LLMResponse with the completion result

        Raises:
            ValueError: If parameters are invalid
            RateLimitError: If rate limit is exceeded
            APIError: If API call fails
        """
        model = model or self.default_model
        self._validate_model(model)

        # Enforce max tokens limit
        max_tokens = min(max_tokens, self.max_tokens)

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            # Build request kwargs
            request_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": openai_messages,
            }

            # Add tools/functions if provided
            if tools and self.supports_tools():
                request_kwargs["tools"] = tools

            # Make API call
            response = await self.client.chat.completions.create(**request_kwargs)

            # Extract content from first choice
            choice = response.choices[0]
            content = choice.message.content or ""

            # Handle tool calls if present
            if choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    content += (
                        f"\n[Tool Call: {tool_call.function.name}]\n"
                        f"{tool_call.function.arguments}"
                    )

            # Track usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            self._track_usage(input_tokens, output_tokens, model, cost)

            logger.debug(
                f"OpenAI completion - Model: {model}, Tokens in: {input_tokens}, "
                f"out: {output_tokens}, Cost: ${cost:.6f}"
            )

            return LLMResponse(
                content=content,
                model=model,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                finish_reason=choice.finish_reason,
                raw_response=response,
            )

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion using OpenAI.

        Yields partial response chunks as they arrive from the API.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default_model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Yields:
            Partial response text chunks

        Raises:
            ValueError: If parameters are invalid
            APIError: If API call fails
        """
        model = model or self.default_model
        self._validate_model(model)

        # Enforce max tokens limit
        max_tokens = min(max_tokens, self.max_tokens)

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            # Use stream context manager for streaming
            with await self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=openai_messages,
                stream=True,
            ) as stream:
                input_tokens = 0
                output_tokens = 0

                async for chunk in stream:
                    # Handle content chunk deltas
                    if (
                        chunk.choices
                        and chunk.choices[0].delta
                        and chunk.choices[0].delta.content
                    ):
                        yield chunk.choices[0].delta.content

                    # Track usage from completion_usage chunks
                    if chunk.usage:
                        input_tokens = chunk.usage.prompt_tokens
                        output_tokens = chunk.usage.completion_tokens

                # Track usage
                if input_tokens > 0 or output_tokens > 0:
                    cost = self._calculate_cost(model, input_tokens, output_tokens)
                    self._track_usage(input_tokens, output_tokens, model, cost)

        except APIError as e:
            logger.error(f"OpenAI streaming API error: {e}")
            raise

    @property
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            'openai'
        """
        return "openai"

    def supports_tools(self) -> bool:
        """Check if this provider supports function/tool calling.

        Returns:
            True (OpenAI supports function calling)
        """
        return True

    def supports_thinking(self) -> bool:
        """Check if this provider supports extended thinking.

        Returns:
            False (standard OpenAI does not have extended thinking)
        """
        return False

    def supports_code_execution(self) -> bool:
        """Check if this provider supports code execution.

        Returns:
            False (OpenAI does not have direct code execution)
        """
        return False

    @staticmethod
    def _validate_model(model: str) -> None:
        """Validate that the model string is a valid OpenAI model.

        Args:
            model: Model identifier to validate

        Raises:
            ValueError: If model is not recognized as an OpenAI model
        """
        # OpenAI models typically start with gpt- or match certain patterns
        if not any(model.startswith(prefix) for prefix in ["gpt-", "text-", "code-"]):
            logger.warning(
                f"Model {model} may not be a valid OpenAI model. "
                "Proceeding anyway as custom models may be used."
            )

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
        for known_model in OPENAI_PRICING:
            if model.startswith(known_model):
                base_model = known_model
                break

        # Default to gpt-4o pricing if model not found
        pricing = OPENAI_PRICING.get(base_model, {"input": 5.00, "output": 15.00})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
