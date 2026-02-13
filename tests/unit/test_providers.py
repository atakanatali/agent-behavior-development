"""Unit tests for orchestify.providers.base module.

Note: Tests for specific providers (claude, openai, litellm) and registry
are skipped when their dependencies have version incompatibilities.
The base module is tested directly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestify.providers.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    TokenUsage,
)


# ─── LLMMessage Tests ───


class TestLLMMessage:
    def test_create_message(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self):
        msg = LLMMessage(role="system", content="You are an AI")
        assert msg.role == "system"

    def test_assistant_message(self):
        msg = LLMMessage(role="assistant", content="I can help")
        assert msg.role == "assistant"


# ─── LLMResponse Tests ───


class TestLLMResponse:
    def test_create_response(self):
        resp = LLMResponse(
            content="Hello world",
            model="claude-3-sonnet",
            tokens_input=10,
            tokens_output=5,
            finish_reason="stop",
        )
        assert resp.content == "Hello world"
        assert resp.model == "claude-3-sonnet"
        assert resp.tokens_input == 10
        assert resp.tokens_output == 5

    def test_optional_fields(self):
        resp = LLMResponse(
            content="Test",
            model="gpt-4",
            tokens_input=0,
            tokens_output=0,
            finish_reason="stop",
        )
        assert resp.raw_response is None


# ─── TokenUsage Tests ───


class TestTokenUsage:
    def test_create_default(self):
        usage = TokenUsage()
        assert usage.total_input == 0
        assert usage.total_output == 0
        assert usage.total_cost_usd == 0.0
        assert usage.call_count == 0

    def test_track_values(self):
        usage = TokenUsage()
        usage.total_input = 100
        usage.total_output = 50
        usage.total_cost_usd = 0.05
        usage.call_count = 1
        assert usage.total_input == 100
        assert usage.total_cost_usd == 0.05


# ─── LLMProvider Abstract Tests ───


class TestLLMProvider:
    def test_cannot_instantiate(self):
        """LLMProvider is abstract."""
        with pytest.raises(TypeError):
            LLMProvider("test-provider", {})

    def test_concrete_provider(self):
        class MockProvider(LLMProvider):
            @property
            def provider_type(self):
                return "mock"

            async def complete(self, messages, **kwargs):
                return LLMResponse(
                    content="Mock", model="mock-1",
                    tokens_input=10, tokens_output=5,
                    finish_reason="stop",
                )

            async def stream(self, messages, **kwargs):
                yield "Mock"

        provider = MockProvider("test-provider", {"default_model": "mock-1"})
        assert provider.provider_type == "mock"
        assert provider.supports_tools() is False

    def test_usage_tracking(self):
        class MockProvider(LLMProvider):
            @property
            def provider_type(self):
                return "mock"

            async def complete(self, messages, **kwargs):
                return LLMResponse(content="x", model="m", tokens_input=0, tokens_output=0, finish_reason="stop")

            async def stream(self, messages, **kwargs):
                yield "x"

        provider = MockProvider("test-provider", {})
        provider._track_usage(100, 50, "model", 0.01)
        usage = provider.get_usage()
        assert usage.total_input == 100
        assert usage.total_output == 50
        assert usage.total_cost_usd == 0.01
        assert usage.call_count == 1

    def test_reset_usage(self):
        class MockProvider(LLMProvider):
            @property
            def provider_type(self):
                return "mock"

            async def complete(self, messages, **kwargs):
                return LLMResponse(content="x", model="m", tokens_input=0, tokens_output=0, finish_reason="stop")

            async def stream(self, messages, **kwargs):
                yield "x"

        provider = MockProvider("test-provider", {})
        provider._track_usage(100, 50, "m", 0.01)
        provider.reset_usage()
        usage = provider.get_usage()
        assert usage.total_input == 0
        assert usage.call_count == 0

    def test_cumulative_tracking(self):
        class MockProvider(LLMProvider):
            @property
            def provider_type(self):
                return "mock"

            async def complete(self, messages, **kwargs):
                return LLMResponse(content="x", model="m", tokens_input=0, tokens_output=0, finish_reason="stop")

            async def stream(self, messages, **kwargs):
                yield "x"

        provider = MockProvider("test-provider", {})
        provider._track_usage(100, 50, "m", 0.01)
        provider._track_usage(200, 100, "m", 0.02)
        usage = provider.get_usage()
        assert usage.total_input == 300
        assert usage.total_output == 150
        assert abs(usage.total_cost_usd - 0.03) < 0.001
        assert usage.call_count == 2
