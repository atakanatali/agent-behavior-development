"""Configuration models and loading for orchestify."""
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectConfig(BaseModel):
    """Project configuration."""

    name: str = Field(..., description="Project name")
    repo: str = Field(..., description="Repository in owner/repo format")
    main_branch: str = Field("main", description="Main branch name")
    branch_prefix: str = Field("feature/", description="Feature branch prefix")

    model_config = {"extra": "forbid"}


class OrchestrationConfig(BaseModel):
    """Orchestration pipeline configuration."""

    max_review_cycles: int = Field(3, ge=1, description="Maximum review cycles per issue")
    max_qa_cycles: int = Field(3, ge=1, description="Maximum QA cycles per issue")
    auto_merge: bool = Field(True, description="Auto-merge PRs after approval")
    sequential_issues: bool = Field(
        True, description="Process issues sequentially or in parallel"
    )

    model_config = {"extra": "forbid"}


class IssueConfig(BaseModel):
    """Issue processing configuration."""

    max_changes_per_issue: int = Field(
        20, ge=1, description="Maximum file changes per issue"
    )
    language: str = Field("en", description="Issue language code")
    require_agent_directive: bool = Field(
        True, description="Require explicit agent directive in issue"
    )
    require_done_checklist: bool = Field(
        True, description="Require done checklist in PR description"
    )

    model_config = {"extra": "forbid"}


class ABDConfig(BaseModel):
    """Agent Behavior Development configuration."""

    scorecard_enabled: bool = Field(True, description="Enable ABD scorecard")
    recycle_mandatory: bool = Field(True, description="Mandatory recycle if scorecard fails")
    evidence_required: bool = Field(
        True, description="Require evidence for scorecard decisions"
    )

    model_config = {"extra": "forbid"}


class DevLoopConfig(BaseModel):
    """Development loop configuration."""

    build_cmd: str = Field("", description="Build command")
    lint_cmd: str = Field("", description="Lint command")
    test_cmd: str = Field("", description="Test command")
    max_self_fix: int = Field(5, ge=1, description="Maximum self-fix attempts")
    timeout_per_command: int = Field(
        120, ge=1, description="Timeout per command in seconds"
    )

    model_config = {"extra": "forbid"}


class AgentConfig(BaseModel):
    """Individual agent configuration."""

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature parameter")
    thinking: bool = Field(False, description="Enable extended thinking")
    mode: str = Field("autonomous", pattern="^(autonomous|interactive)$")
    max_tokens: int = Field(8192, ge=1, description="Maximum tokens for response")

    model_config = {"extra": "forbid"}


class AgentsConfig(BaseModel):
    """All agents configuration."""

    agents: Dict[str, AgentConfig] = Field(
        default_factory=dict, description="Agent configurations by name"
    )

    model_config = {"extra": "forbid"}


class ProviderConfig(BaseModel):
    """Individual provider configuration."""

    type: str = Field(
        ..., pattern="^(anthropic|openai|litellm)$", description="Provider type"
    )
    api_key: str = Field(..., description="API key (supports ${ENV_VAR} substitution)")
    default_model: str = Field(..., description="Default model identifier")
    max_tokens: int = Field(8192, ge=1, description="Maximum tokens")
    base_url: Optional[str] = Field(None, description="Custom base URL for API")

    model_config = {"extra": "forbid"}


class ProvidersConfig(BaseModel):
    """All providers configuration."""

    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Provider configurations by name"
    )

    model_config = {"extra": "forbid"}


class MemoryLayerConfig(BaseModel):
    """Individual memory layer configuration."""

    ttl: Optional[str] = Field(None, description="Time-to-live for entries")
    max_entries: int = Field(1000, ge=1, description="Maximum entries in layer")

    model_config = {"extra": "forbid"}


class ContextifyConfig(BaseModel):
    """Contextify memory configuration."""

    enabled: bool = Field(False, description="Enable Contextify")
    host: str = Field("http://localhost:8080", description="Contextify host URL")
    protocol: str = Field("http", pattern="^(http|https)$", description="Protocol")
    layers: Dict[str, MemoryLayerConfig] = Field(
        default_factory=lambda: {
            "agent": MemoryLayerConfig(ttl=None, max_entries=1000),
            "epic": MemoryLayerConfig(ttl=None, max_entries=1000),
            "global": MemoryLayerConfig(ttl=None, max_entries=1000),
        },
        description="Memory layers",
    )

    model_config = {"extra": "forbid"}


class FallbackMemoryConfig(BaseModel):
    """Fallback memory configuration."""

    type: str = Field("local_json", description="Fallback memory type")
    path: str = Field(".orchestify/memory/", description="Local memory path")

    model_config = {"extra": "forbid"}


class MemoryConfig(BaseModel):
    """Memory configuration."""

    contextify: ContextifyConfig = Field(
        default_factory=ContextifyConfig, description="Contextify settings"
    )
    fallback: FallbackMemoryConfig = Field(
        default_factory=FallbackMemoryConfig, description="Fallback memory settings"
    )

    model_config = {"extra": "forbid"}


class OrchestrifyConfig(BaseModel):
    """Root configuration aggregating all sub-configurations."""

    project: ProjectConfig = Field(..., description="Project configuration")
    orchestration: OrchestrationConfig = Field(
        default_factory=OrchestrationConfig, description="Orchestration settings"
    )
    issue: IssueConfig = Field(
        default_factory=IssueConfig, description="Issue processing settings"
    )
    abd: ABDConfig = Field(default_factory=ABDConfig, description="ABD settings")
    dev_loop: DevLoopConfig = Field(
        default_factory=DevLoopConfig, description="Development loop settings"
    )
    agents: AgentsConfig = Field(
        default_factory=AgentsConfig, description="Agents configuration"
    )
    providers: ProvidersConfig = Field(
        default_factory=ProvidersConfig, description="Providers configuration"
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig, description="Memory configuration"
    )

    model_config = {"extra": "forbid"}

    @field_validator("agents", "providers", mode="before")
    @classmethod
    def handle_legacy_format(cls, v: Any, info: Any) -> Any:
        """Handle both flat and nested config formats."""
        if isinstance(v, dict):
            field_name = info.field_name  # 'agents' or 'providers'
            # If it's already in the expected format, return as-is
            if field_name in v:
                return v
            # Otherwise wrap it with the correct field name
            return {field_name: v}
        return v


def _substitute_env_vars(text: str) -> str:
    """Substitute environment variables in format ${VAR_NAME}."""
    pattern = r"\$\{([^}]+)\}"

    def replace_env(match: Any) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replace_env, text)


def _load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML file and substitute environment variables."""
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    # Recursively substitute environment variables
    def substitute_recursive(obj: Any) -> Any:
        if isinstance(obj, str):
            return _substitute_env_vars(obj)
        elif isinstance(obj, dict):
            return {k: substitute_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute_recursive(item) for item in obj]
        return obj

    return substitute_recursive(data)


def load_config(config_dir: Path) -> OrchestrifyConfig:
    """
    Load orchestify configuration from YAML files in config directory.

    Args:
        config_dir: Path to configuration directory containing YAML files

    Returns:
        OrchestrifyConfig: Fully loaded and validated configuration

    Raises:
        FileNotFoundError: If required config files are missing
        ValueError: If configuration is invalid
    """
    config_dir = Path(config_dir)

    # Load main configuration
    orchestify_path = config_dir / "orchestify.yaml"
    orchestify_data = _load_yaml(orchestify_path)

    # Load agents configuration
    agents_path = config_dir / "agents.yaml"
    agents_data = _load_yaml(agents_path) if agents_path.exists() else {}

    # Load providers configuration
    providers_path = config_dir / "providers.yaml"
    providers_data = _load_yaml(providers_path) if providers_path.exists() else {}

    # Load memory configuration
    memory_path = config_dir / "memory.yaml"
    memory_data = _load_yaml(memory_path) if memory_path.exists() else {}

    # Merge all data
    config_data = {
        **orchestify_data,
        "agents": agents_data.get("agents", {}),
        "providers": providers_data.get("providers", {}),
        "memory": memory_data.get("contextify") or memory_data,
    }

    # Validate and create config object
    try:
        return OrchestrifyConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {str(e)}") from e


def validate_config(config: OrchestrifyConfig) -> List[str]:
    """
    Validate configuration and return list of warnings.

    Args:
        config: Configuration to validate

    Returns:
        List of validation warnings (empty list if all OK)
    """
    warnings: List[str] = []

    # Check that all agent providers exist
    for agent_name, agent in config.agents.agents.items():
        if agent.provider not in config.providers.providers:
            warnings.append(
                f"Agent '{agent_name}' references unknown provider '{agent.provider}'"
            )

    # Check that all providers have valid types
    for provider_name, provider in config.providers.providers.items():
        if provider.type not in ("anthropic", "openai", "litellm"):
            warnings.append(
                f"Provider '{provider_name}' has unknown type '{provider.type}'"
            )

    # Check that at least one agent is configured
    if not config.agents.agents:
        warnings.append("No agents configured")

    # Check that at least one provider is configured
    if not config.providers.providers:
        warnings.append("No providers configured")

    # Check dev loop timeouts are reasonable
    if config.dev_loop.timeout_per_command > 3600:
        warnings.append(
            f"Dev loop timeout ({config.dev_loop.timeout_per_command}s) is very long"
        )

    # Check memory configuration
    if config.memory.contextify.enabled:
        if not config.memory.contextify.host:
            warnings.append("Contextify enabled but no host configured")
    else:
        # Fallback memory should have a valid path
        memory_path = Path(config.memory.fallback.path)
        if not memory_path.is_absolute() and not memory_path.is_dir():
            warnings.append(
                f"Fallback memory path '{config.memory.fallback.path}' does not exist"
            )

    return warnings
