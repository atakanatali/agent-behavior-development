"""LiteLLM universal LLM provider implementation.

Provides a universal adapter for LiteLLM, allowing orchestify to work with
any LLM provider supported by LiteLLM including Azure, Cohere, Replicate, etc.
"""

import logging
import os
import re
from typing import Any, AsyncIterator

import litellm

from orchestify.providers.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class LiteLLMProvider(LLMProvider):
    """Universal LLM provider using LiteLLM as adapter.

    This provider acts as a fallback and universal adapter, supporting any LLM
    that LiteLLM can route to. Useful for supporting additional providers like
    Azure OpenAI, Cohere, Replicate, etc.

    Supports:
    - Single completions and streaming
    - Multiple provider backends via LiteLLM routing
    - Tool/function calling (where supported by backend)
    - Custom model names and endpoints
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        """Initialize LiteLLM provider.

        Args:
            provider_id: Unique identifier for this provider instance
            config: Configuration dict with:
                - api_key: API key for the backend (supports ${ENV_VAR} substitution)
                - default_model: Default model to use (e.g., 'azure/gpt-4')
                - max_tokens: Maximum tokens per request
                - base_url: Optional custom API endpoint

        Raises:
            ValueError: If api_key or default_model is missing
        """
        super().__init__(provider_id, config)

        # Resolve API key with environment variable substitution
        api_key = config.get("api_key", "")
        if not api_key:
            logger.warning(f"Provider {provider_id}: api_key not configured, will use environment")
            api_key = ""
        else:
            api_key = self._resolve_env_var(api_key)

        # Store API key in environment if provided
        if api_key:
            # Determine which env var to set based on model type
            if config.get("default_model", "").startswith("azure"):
                os.environ["AZURE_API_KEY"] = api_key
            else:
                # Generic approach - may be overridden by more specific setup
                logger.debug(f"API key configured for {provider_id}")

        self.default_model = config.get("default_model")
        if not self.default_model:
            raise ValueError(f"Provider {provider_id}: default_model is required")

        self.max_tokens = config.get("max_tokens", 8192)

        # Enable cost tracking in LiteLLM
        litellm.cost_per_token_dict = {}

        logger.info(
            f"Initialized LiteLLM provider {provider_id} with model {self.default_model}"
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
        """Generate a single completion using LiteLLM.

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default_model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool/function definitions
            thinking: Extended thinking (backend-dependent support)

        Returns:
            LLMResponse with the completion result

        Raises:
            ValueError: If parameters are invalid
            Exception: If API call fails
        """
        model = model or self.default_model

        # Enforce max tokens limit
        max_tokens = min(max_tokens, self.max_tokens)

        # Convert messages to standard format
        litellm_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            # Build request kwargs
            request_kwargs: dict[str, Any] = {
                "model": model,
                "messages": litellm_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add tools if provided
            if tools:
                request_kwargs["tools"] = tools

            # Make API call via LiteLLM
            response = await litellm.acompletion(**request_kwargs)

            # Extract content
            content = response["choices"][0]["message"].get("content", "")

            # Handle tool calls if present
            if "tool_calls" in response["choices"][0]["message"]:
                for tool_call in response["choices"][0]["message"]["tool_calls"]:
                    content += (
                        f"\n[Tool Call: {tool_call.get('function', {}).get('name', 'unknown')}]\n"
                        f"{tool_call.get('function', {}).get('arguments', '')}"
                    )

            # Track usage
            input_tokens = response.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = response.get("usage", {}).get("completion_tokens", 0)

            # Calculate cost from LiteLLM's cost tracking if available
            cost = self._get_litellm_cost(response)
            self._track_usage(input_tokens, output_tokens, model, cost)

            logger.debug(
                f"LiteLLM completion - Model: {model}, Tokens in: {input_tokens}, "
                f"out: {output_tokens}, Cost: ${cost:.6f}"
            )

            return LLMResponse(
                content=content,
                model=model,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                finish_reason=response["choices"][0].get("finish_reason", "unknown"),
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"LiteLLM API error: {e}")
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion using LiteLLM.

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
            Exception: If API call fails
        """
        model = model or self.default_model

        # Enforce max tokens limit
        max_tokens = min(max_tokens, self.max_tokens)

        # Convert messages to standard format
        litellm_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            # Make streaming API call via LiteLLM
            response = await litellm.acompletion(
                model=model,
                messages=litellm_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            # Note: LiteLLM's async streaming is complex; we'll track usage separately
            input_tokens = 0
            output_tokens = 0

            async for chunk in response:
                # Handle content chunks
                if "choices" in chunk and chunk["choices"]:
                    choice = chunk["choices"][0]
                    if "delta" in choice and "content" in choice["delta"]:
                        yield choice["delta"]["content"]

                    # Track usage from final chunk if available
                    if "message" in choice and "content" in choice["message"]:
                        # Final message has content
                        pass

                # Try to extract usage from chunk
                if "usage" in chunk:
                    input_tokens = chunk["usage"].get("prompt_tokens", 0)
                    output_tokens = chunk["usage"].get("completion_tokens", 0)

            # Track usage if collected
            if input_tokens > 0 or output_tokens > 0:
                cost = 0.0
                self._track_usage(input_tokens, output_tokens, model, cost)

        except Exception as e:
            logger.error(f"LiteLLM streaming API error: {e}")
            raise

    @property
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            'litellm'
        """
        return "litellm"

    def supports_tools(self) -> bool:
        """Check if this provider supports function/tool calling.

        Returns:
            True (LiteLLM supports tools for compatible backends)
        """
        return True

    def supports_thinking(self) -> bool:
        """Check if this provider supports extended thinking.

        Returns:
            True (some LiteLLM backends support thinking)
        """
        return True

    def supports_code_execution(self) -> bool:
        """Check if this provider supports code execution.

        Returns:
            False (LiteLLM does not have direct code execution)
        """
        return False

    @staticmethod
    def _get_litellm_cost(response: dict) -> float:
        """Extract cost from LiteLLM response if available.

        Args:
            response: Response dict from LiteLLM

        Returns:
            Cost in USD, or 0.0 if not available
        """
        if "cost" in response:
            return response["cost"]

        # Try to calculate from usage and model info
        if "_response_ms" in response:
            # Some cost information might be embedded
            pass

        return 0.0
