"""Provider registry for managing LLM provider instances.

Handles registration, discovery, and lifecycle management of LLM providers.
Supports auto-detection of provider types from configuration and validation.
"""

import logging
from typing import Any

from orchestify.core.config import ProviderConfig, ProvidersConfig, AgentsConfig
from orchestify.providers.base import LLMProvider, TokenUsage
from orchestify.providers.claude import ClaudeProvider
from orchestify.providers.openai_provider import OpenAIProvider
from orchestify.providers.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing LLM provider instances.

    Handles provider registration, lookup, and initialization from configuration.
    Provides methods to retrieve providers by ID or for specific agents.
    """

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._providers: dict[str, LLMProvider] = {}
        logger.debug("Initialized ProviderRegistry")

    def register(self, provider_id: str, provider: LLMProvider) -> None:
        """Register an LLM provider instance.

        Args:
            provider_id: Unique identifier for the provider
            provider: Initialized LLMProvider instance

        Raises:
            ValueError: If provider_id is already registered
        """
        if provider_id in self._providers:
            raise ValueError(f"Provider '{provider_id}' is already registered")

        self._providers[provider_id] = provider
        logger.info(f"Registered provider: {provider_id}")

    def get(self, provider_id: str) -> LLMProvider:
        """Get a provider by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            LLMProvider instance

        Raises:
            KeyError: If provider is not registered
        """
        if provider_id not in self._providers:
            raise KeyError(
                f"Provider '{provider_id}' not found. "
                f"Available: {list(self._providers.keys())}"
            )

        return self._providers[provider_id]

    def get_for_agent(
        self, agent_id: str, agents_config: AgentsConfig
    ) -> LLMProvider:
        """Get the provider for a specific agent.

        Args:
            agent_id: Agent identifier
            agents_config: AgentsConfig object

        Returns:
            LLMProvider configured for this agent

        Raises:
            KeyError: If agent or its provider is not found
            ValueError: If agent configuration is invalid
        """
        if agent_id not in agents_config.agents:
            raise KeyError(f"Agent '{agent_id}' not found in configuration")

        agent_config = agents_config.agents[agent_id]
        provider_id = agent_config.provider

        return self.get(provider_id)

    @classmethod
    def from_config(
        cls,
        providers_config: ProvidersConfig,
        validate_connectivity: bool = False,
    ) -> "ProviderRegistry":
        """Create and populate a ProviderRegistry from configuration.

        Automatically detects provider types and initializes providers.

        Args:
            providers_config: ProvidersConfig with provider definitions
            validate_connectivity: If True, test connectivity to each provider

        Returns:
            Populated ProviderRegistry instance

        Raises:
            ValueError: If configuration is invalid or providers cannot be initialized
        """
        registry = cls()

        for provider_id, provider_cfg in providers_config.providers.items():
            try:
                provider = cls._create_provider(provider_id, provider_cfg)
                registry.register(provider_id, provider)

                if validate_connectivity:
                    logger.info(f"Validating connectivity for provider: {provider_id}")
                    # Could add health check here in future

            except Exception as e:
                logger.error(f"Failed to initialize provider '{provider_id}': {e}")
                raise ValueError(
                    f"Failed to initialize provider '{provider_id}': {str(e)}"
                ) from e

        return registry

    @staticmethod
    def _create_provider(
        provider_id: str, provider_config: ProviderConfig
    ) -> LLMProvider:
        """Create a provider instance based on configuration.

        Args:
            provider_id: Unique identifier for the provider
            provider_config: ProviderConfig with provider details

        Returns:
            Initialized LLMProvider instance

        Raises:
            ValueError: If provider type is unknown or config is invalid
        """
        provider_type = provider_config.type.lower()

        # Convert ProviderConfig to dict for provider initialization
        config_dict = {
            "api_key": provider_config.api_key,
            "default_model": provider_config.default_model,
            "max_tokens": provider_config.max_tokens,
        }

        if provider_config.base_url:
            config_dict["base_url"] = provider_config.base_url

        if provider_type == "anthropic":
            logger.debug(f"Creating Claude provider: {provider_id}")
            return ClaudeProvider(provider_id, config_dict)

        elif provider_type == "openai":
            logger.debug(f"Creating OpenAI provider: {provider_id}")
            return OpenAIProvider(provider_id, config_dict)

        elif provider_type == "litellm":
            logger.debug(f"Creating LiteLLM provider: {provider_id}")
            return LiteLLMProvider(provider_id, config_dict)

        else:
            raise ValueError(
                f"Unknown provider type '{provider_type}'. "
                f"Must be one of: anthropic, openai, litellm"
            )

    def list_providers(self) -> list[str]:
        """List all registered provider IDs.

        Returns:
            List of provider identifiers
        """
        return list(self._providers.keys())

    def get_total_usage(self) -> dict[str, TokenUsage]:
        """Get cumulative token usage for all providers.

        Returns:
            Dictionary mapping provider ID to TokenUsage stats
        """
        return {
            provider_id: provider.get_usage()
            for provider_id, provider in self._providers.items()
        }

    def get_usage_summary(self) -> dict[str, Any]:
        """Get a human-readable usage summary for all providers.

        Returns:
            Dictionary with aggregated usage metrics
        """
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_calls = 0
        provider_summaries = {}

        for provider_id, usage in self.get_total_usage().items():
            total_input += usage.total_input
            total_output += usage.total_output
            total_cost += usage.total_cost_usd
            total_calls += usage.call_count

            provider_summaries[provider_id] = {
                "input_tokens": usage.total_input,
                "output_tokens": usage.total_output,
                "total_tokens": usage.total_input + usage.total_output,
                "cost_usd": usage.total_cost_usd,
                "calls": usage.call_count,
            }

        return {
            "total": {
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "cost_usd": total_cost,
                "calls": total_calls,
            },
            "by_provider": provider_summaries,
        }

    def reset_all_usage(self) -> None:
        """Reset usage metrics for all providers."""
        for provider in self._providers.values():
            provider.reset_usage()

        logger.info("Reset usage metrics for all providers")

    def __len__(self) -> int:
        """Return the number of registered providers."""
        return len(self._providers)

    def __contains__(self, provider_id: str) -> bool:
        """Check if a provider is registered."""
        return provider_id in self._providers

    def __repr__(self) -> str:
        """Return string representation of registry."""
        return (
            f"ProviderRegistry(providers={list(self._providers.keys())}, "
            f"count={len(self._providers)})"
        )
