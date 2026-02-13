"""
LLM Routing Logic for Agent-based Provider Selection.

Routes agent requests to the correct LLM provider based on configuration.
Provides agent-specific model selection, parameters, and aggregated usage tracking.
"""

import logging
from typing import Any, Dict, Optional

from orchestify.providers.base import LLMProvider, TokenUsage

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Routes agent requests to the correct LLM provider.

    Manages provider selection, model configuration, and parameter resolution
    for different agents. Supports provider and model configuration per agent
    with defaults from provider configuration.

    Attributes:
        registry: ProviderRegistry instance containing all available providers
        agents_config: AgentsConfig with agent-specific configurations
        provider_cache: Cache of provider instances by agent_id
    """

    def __init__(
        self, provider_registry: Any, agents_config: Any
    ) -> None:
        """
        Initialize the LLM router.

        Args:
            provider_registry: ProviderRegistry instance with available providers
            agents_config: AgentsConfig with agent configurations

        Raises:
            ValueError: If configuration is invalid or missing required agents/providers
        """
        self.registry = provider_registry
        self.agents_config = agents_config
        self.provider_cache: Dict[str, LLMProvider] = {}

        logger.debug(
            f"Initializing LLMRouter with {len(agents_config.agents)} agents"
        )

        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """
        Validate that all agent providers are available.

        Raises:
            ValueError: If any agent references a non-existent provider
        """
        for agent_id, agent_config in self.agents_config.agents.items():
            provider_name = agent_config.provider
            if not self.registry.has_provider(provider_name):
                raise ValueError(
                    f"Agent '{agent_id}' references unknown provider '{provider_name}'"
                )
            logger.debug(f"Validated agent '{agent_id}' -> provider '{provider_name}'")

    def get_provider_for_agent(self, agent_id: str) -> LLMProvider:
        """
        Get the configured LLM provider for a specific agent.

        Caches provider instances to avoid repeated registry lookups.

        Args:
            agent_id: Agent identifier

        Returns:
            LLMProvider instance for the agent

        Raises:
            ValueError: If agent or provider not found
        """
        # Check cache first
        if agent_id in self.provider_cache:
            logger.debug(f"Retrieved provider from cache for agent '{agent_id}'")
            return self.provider_cache[agent_id]

        # Get agent configuration
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]
        provider_name = agent_config.provider

        # Get provider from registry
        try:
            provider = self.registry.get_provider(provider_name)
            self.provider_cache[agent_id] = provider
            logger.debug(
                f"Retrieved provider '{provider_name}' for agent '{agent_id}'"
            )
            return provider
        except ValueError as e:
            raise ValueError(f"Failed to get provider for agent '{agent_id}': {e}")

    def get_model_for_agent(self, agent_id: str) -> str:
        """
        Get the configured model for a specific agent.

        Returns agent-specific model if configured, otherwise returns
        the provider's default model.

        Args:
            agent_id: Agent identifier

        Returns:
            Model identifier string

        Raises:
            ValueError: If agent not found
        """
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]
        model = agent_config.model

        logger.debug(f"Got model '{model}' for agent '{agent_id}'")
        return model

    def get_temperature_for_agent(self, agent_id: str) -> float:
        """
        Get configured temperature parameter for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Temperature value (0.0 to 2.0)

        Raises:
            ValueError: If agent not found
        """
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]
        temperature = agent_config.temperature

        logger.debug(f"Got temperature {temperature} for agent '{agent_id}'")
        return temperature

    def get_max_tokens_for_agent(self, agent_id: str) -> int:
        """
        Get configured maximum tokens for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Maximum tokens value

        Raises:
            ValueError: If agent not found
        """
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]
        max_tokens = agent_config.max_tokens

        logger.debug(f"Got max_tokens {max_tokens} for agent '{agent_id}'")
        return max_tokens

    def supports_thinking_for_agent(self, agent_id: str) -> bool:
        """
        Check if extended thinking is enabled for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if thinking is enabled and supported, False otherwise

        Raises:
            ValueError: If agent not found
        """
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]

        # Check if thinking is enabled in config
        if not agent_config.thinking:
            return False

        # Check if provider supports thinking
        try:
            provider = self.get_provider_for_agent(agent_id)
            supports = provider.supports_thinking()
            logger.debug(
                f"Agent '{agent_id}' thinking support: {supports} "
                f"(enabled in config: {agent_config.thinking})"
            )
            return supports
        except ValueError as e:
            logger.warning(f"Failed to check thinking support: {e}")
            return False

    def get_agent_mode(self, agent_id: str) -> str:
        """
        Get the operational mode for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Mode string ('autonomous' or 'interactive')

        Raises:
            ValueError: If agent not found
        """
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]
        mode = agent_config.mode

        logger.debug(f"Got mode '{mode}' for agent '{agent_id}'")
        return mode

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get full agent configuration.

        Returns the complete configuration object for an agent,
        including provider info and all parameters.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with agent configuration

        Raises:
            ValueError: If agent not found
        """
        if agent_id not in self.agents_config.agents:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        agent_config = self.agents_config.agents[agent_id]

        # Get provider to include in response
        try:
            provider = self.get_provider_for_agent(agent_id)
            provider_info = {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type,
            }
        except ValueError:
            provider_info = {"provider_id": None, "provider_type": None}

        config_dict = {
            "agent_id": agent_id,
            "provider": agent_config.provider,
            "model": agent_config.model,
            "temperature": agent_config.temperature,
            "thinking": agent_config.thinking,
            "mode": agent_config.mode,
            "max_tokens": agent_config.max_tokens,
            **provider_info,
        }

        logger.debug(f"Retrieved full config for agent '{agent_id}'")
        return config_dict

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configurations for all agents.

        Returns:
            Dictionary mapping agent_id to agent configuration
        """
        agents = {}
        for agent_id in self.agents_config.agents:
            try:
                agents[agent_id] = self.get_agent_config(agent_id)
            except ValueError as e:
                logger.warning(f"Failed to get config for agent '{agent_id}': {e}")

        logger.debug(f"Retrieved configs for {len(agents)} agents")
        return agents

    def get_total_usage(self) -> Dict[str, Any]:
        """
        Get aggregated token usage across all providers.

        Accumulates usage statistics from all providers in the registry.

        Returns:
            Dictionary with aggregated usage statistics:
                - total_input: Total input tokens across all providers
                - total_output: Total output tokens across all providers
                - total_cost_usd: Estimated total cost across all providers
                - total_calls: Total API calls across all providers
                - providers: Dictionary of usage per provider
        """
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_calls = 0
        provider_usage = {}

        # Aggregate usage from all providers
        for provider_id, provider in self.registry.providers.items():
            usage = provider.get_usage()
            total_input += usage.total_input
            total_output += usage.total_output
            total_cost += usage.total_cost_usd
            total_calls += usage.call_count

            provider_usage[provider_id] = {
                "total_input": usage.total_input,
                "total_output": usage.total_output,
                "total_cost_usd": usage.total_cost_usd,
                "call_count": usage.call_count,
            }

        result = {
            "total_input": total_input,
            "total_output": total_output,
            "total_cost_usd": total_cost,
            "total_calls": total_calls,
            "providers": provider_usage,
        }

        logger.debug(
            f"Aggregated usage - Input: {total_input}, Output: {total_output}, "
            f"Cost: ${total_cost:.6f}, Calls: {total_calls}"
        )

        return result

    def get_provider_usage(self, provider_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Dictionary with provider usage statistics

        Raises:
            ValueError: If provider not found
        """
        if not self.registry.has_provider(provider_id):
            raise ValueError(f"Provider '{provider_id}' not found in registry")

        provider = self.registry.get_provider(provider_id)
        usage = provider.get_usage()

        usage_dict = {
            "provider_id": provider_id,
            "provider_type": provider.provider_type,
            "total_input": usage.total_input,
            "total_output": usage.total_output,
            "total_cost_usd": usage.total_cost_usd,
            "call_count": usage.call_count,
        }

        logger.debug(
            f"Retrieved usage for provider '{provider_id}': {usage_dict}"
        )

        return usage_dict

    def reset_usage(self, provider_id: Optional[str] = None) -> None:
        """
        Reset usage statistics.

        Args:
            provider_id: Specific provider to reset, or None to reset all providers

        Raises:
            ValueError: If provider not found (when provider_id specified)
        """
        if provider_id:
            if not self.registry.has_provider(provider_id):
                raise ValueError(f"Provider '{provider_id}' not found in registry")

            provider = self.registry.get_provider(provider_id)
            provider.reset_usage()
            logger.info(f"Reset usage for provider '{provider_id}'")
        else:
            # Reset all providers
            for provider_id_iter, provider in self.registry.providers.items():
                provider.reset_usage()
            logger.info("Reset usage for all providers")

    def list_agents(self) -> list[str]:
        """
        Get list of all configured agent IDs.

        Returns:
            List of agent identifiers
        """
        agents = list(self.agents_config.agents.keys())
        logger.debug(f"Listed {len(agents)} agents")
        return agents

    def list_providers(self) -> list[str]:
        """
        Get list of all configured provider IDs.

        Returns:
            List of provider identifiers
        """
        providers = list(self.registry.providers.keys())
        logger.debug(f"Listed {len(providers)} providers")
        return providers

    def validate_agent(self, agent_id: str) -> bool:
        """
        Validate that an agent is properly configured.

        Checks that the agent exists, its provider exists, and all
        parameters are valid.

        Args:
            agent_id: Agent identifier to validate

        Returns:
            True if agent is valid, False otherwise
        """
        try:
            if agent_id not in self.agents_config.agents:
                logger.warning(f"Agent '{agent_id}' not found")
                return False

            agent_config = self.agents_config.agents[agent_id]

            # Check provider exists
            if not self.registry.has_provider(agent_config.provider):
                logger.warning(
                    f"Agent '{agent_id}' references unknown provider "
                    f"'{agent_config.provider}'"
                )
                return False

            # Check provider type supports thinking if required
            if agent_config.thinking:
                provider = self.get_provider_for_agent(agent_id)
                if not provider.supports_thinking():
                    logger.warning(
                        f"Agent '{agent_id}' has thinking enabled but provider "
                        f"'{agent_config.provider}' does not support it"
                    )

            logger.debug(f"Agent '{agent_id}' validation passed")
            return True

        except Exception as e:
            logger.error(f"Error validating agent '{agent_id}': {e}")
            return False

    def validate_all_agents(self) -> Dict[str, bool]:
        """
        Validate all configured agents.

        Returns:
            Dictionary mapping agent_id to validation result
        """
        results = {}
        for agent_id in self.agents_config.agents:
            results[agent_id] = self.validate_agent(agent_id)

        valid_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Validated {valid_count}/{len(results)} agents successfully"
        )

        return results

    def __repr__(self) -> str:
        """Return string representation."""
        agent_count = len(self.agents_config.agents)
        provider_count = len(self.registry.providers)
        return f"LLMRouter(agents={agent_count}, providers={provider_count})"
