"""
Global configuration manager for orchestify.

Manages user-level config at ~/.orchestify/config/global.yaml.
The ~/.orchestify/ directory is the global home for orchestify, containing:
  - config/         Global settings (global.yaml)
  - data/           SQLite database (orchestify.db)
  - personas/       Agent persona definitions
  - prompts/        Prompt templates
  - rules/          Behavior rules
  - skills/         Agent skills
  - workflows/      Workflow definitions

Hierarchy: Global (~/.orchestify/) -> Project (config/) -> Sprint
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# ── Global Home ──────────────────────────────────────────────────────

def get_orchestify_home() -> Path:
    """
    Get the global orchestify home directory.

    Default: ~/.orchestify/
    Override: ORCHESTIFY_HOME environment variable
    """
    env_home = os.environ.get("ORCHESTIFY_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".orchestify"


# Standard subdirectories within ~/.orchestify/
GLOBAL_SUBDIRS = [
    "config",
    "data",
    "artifacts",
    "personas",
    "prompts",
    "rules",
    "skills",
    "workflows",
]


def ensure_global_home() -> Path:
    """
    Ensure the global ~/.orchestify/ directory exists with all subdirectories.

    Returns:
        Path to the global home
    """
    home = get_orchestify_home()
    home.mkdir(parents=True, exist_ok=True)
    for subdir in GLOBAL_SUBDIRS:
        (home / subdir).mkdir(exist_ok=True)
    return home


# ── Default Config ───────────────────────────────────────────────────

DEFAULT_GLOBAL_CONFIG = {
    "user": {
        "name": "",
        "email": "",
    },
    "defaults": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "language": "en",
    },
    "api_keys": {
        "anthropic": "${ANTHROPIC_API_KEY}",
        "openai": "${OPENAI_API_KEY}",
    },
    "preferences": {
        "theme": "auto",
        "verbose": False,
        "auto_merge": False,
        "sequential_issues": True,
        "max_review_cycles": 3,
        "max_qa_cycles": 3,
    },
}


# ── Config Paths ─────────────────────────────────────────────────────

def get_global_config_dir() -> Path:
    """Get the global config directory path."""
    return get_orchestify_home() / "config"


def get_global_config_path() -> Path:
    """Get the global config file path."""
    return get_global_config_dir() / "global.yaml"


def load_global_config() -> Dict[str, Any]:
    """
    Load global configuration.

    Returns default config merged with any existing user config.
    """
    config_path = get_global_config_path()

    config = DEFAULT_GLOBAL_CONFIG.copy()

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, user_config)
        except (yaml.YAMLError, IOError):
            pass

    # Resolve environment variables
    config = _resolve_env_vars(config)

    return config


def save_global_config(config: Dict[str, Any]) -> Path:
    """
    Save global configuration to disk.

    Args:
        config: Configuration dictionary

    Returns:
        Path to saved config file
    """
    config_dir = get_global_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = get_global_config_path()

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return config_path


def is_installed() -> bool:
    """Check if orchestify has been installed (global config exists)."""
    return get_global_config_path().exists()


def get_api_key(provider: str) -> Optional[str]:
    """
    Get API key for a provider.

    Checks: global config -> environment variables.
    """
    config = load_global_config()
    key = config.get("api_keys", {}).get(provider, "")

    if key and not key.startswith("${"):
        return key

    # Try environment variable
    env_var = f"{provider.upper()}_API_KEY"
    return os.environ.get(env_var)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_env_vars(config: Any) -> Any:
    """Recursively resolve ${ENV_VAR} patterns in config values."""
    if isinstance(config, dict):
        return {k: _resolve_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_resolve_env_vars(v) for v in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.environ.get(env_var, config)
    return config
