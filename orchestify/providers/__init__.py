"""LLM Provider layer for orchestify.

This module provides a unified interface for interacting with multiple LLM providers
including Anthropic Claude, OpenAI, and universal providers via LiteLLM.

Provider implementations are imported lazily to avoid import errors when
optional dependencies (anthropic, openai, litellm) are not installed.
"""

from orchestify.providers.base import (
    LLMMessage,
    LLMResponse,
    TokenUsage,
    LLMProvider,
)

# Lazy imports for concrete providers to avoid dependency issues
try:
    from orchestify.providers.claude import ClaudeProvider
except ImportError:
    ClaudeProvider = None  # type: ignore

try:
    from orchestify.providers.openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None  # type: ignore

try:
    from orchestify.providers.litellm_provider import LiteLLMProvider
except ImportError:
    LiteLLMProvider = None  # type: ignore

try:
    from orchestify.providers.registry import ProviderRegistry
except ImportError:
    ProviderRegistry = None  # type: ignore

__all__ = [
    # Base classes and data models
    "LLMMessage",
    "LLMResponse",
    "TokenUsage",
    "LLMProvider",
    # Concrete providers
    "ClaudeProvider",
    "OpenAIProvider",
    "LiteLLMProvider",
    # Registry
    "ProviderRegistry",
]
