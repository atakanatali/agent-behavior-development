"""Unit tests for orchestify.core.global_config module."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from orchestify.core.global_config import (
    DEFAULT_GLOBAL_CONFIG,
    get_global_config_dir,
    get_global_config_path,
    load_global_config,
    save_global_config,
    is_installed,
    get_api_key,
    _deep_merge,
    _resolve_env_vars,
)


class TestGlobalConfigPaths:
    def test_default_config_dir(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("XDG_CONFIG_HOME", None)
            config_dir = get_global_config_dir()
            assert config_dir == Path.home() / ".config" / "orchestify"

    def test_xdg_config_dir(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/xdg"}):
            config_dir = get_global_config_dir()
            assert config_dir == Path("/tmp/xdg/orchestify")

    def test_config_path(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("XDG_CONFIG_HOME", None)
            config_path = get_global_config_path()
            assert config_path.name == "global.yaml"


class TestGlobalConfigIO:
    def test_save_and_load(self, tmp_path):
        config_dir = tmp_path / "config" / "orchestify"
        config_file = config_dir / "global.yaml"

        with patch("orchestify.core.global_config.get_global_config_dir", return_value=config_dir):
            with patch("orchestify.core.global_config.get_global_config_path", return_value=config_file):
                config = {"user": {"name": "Test User"}, "defaults": {"provider": "anthropic"}}
                save_global_config(config)
                assert config_file.exists()

                loaded = load_global_config()
                assert loaded["user"]["name"] == "Test User"

    def test_load_default_when_no_file(self, tmp_path):
        config_dir = tmp_path / "nonexistent"
        config_file = config_dir / "global.yaml"

        with patch("orchestify.core.global_config.get_global_config_dir", return_value=config_dir):
            with patch("orchestify.core.global_config.get_global_config_path", return_value=config_file):
                config = load_global_config()
                assert config["defaults"]["provider"] == "anthropic"

    def test_is_installed_false(self, tmp_path):
        config_file = tmp_path / "nonexistent" / "global.yaml"
        with patch("orchestify.core.global_config.get_global_config_path", return_value=config_file):
            assert is_installed() is False

    def test_is_installed_true(self, tmp_path):
        config_file = tmp_path / "global.yaml"
        config_file.write_text("user: {name: test}")
        with patch("orchestify.core.global_config.get_global_config_path", return_value=config_file):
            assert is_installed() is True


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        result = _deep_merge(base, override)
        assert result["a"]["x"] == 1
        assert result["a"]["y"] == 99
        assert result["a"]["z"] == 100
        assert result["b"] == 3


class TestResolveEnvVars:
    def test_resolve_existing_env_var(self):
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            result = _resolve_env_vars("${TEST_KEY}")
            assert result == "test_value"

    def test_keep_unresolved(self):
        os.environ.pop("NONEXISTENT_KEY", None)
        result = _resolve_env_vars("${NONEXISTENT_KEY}")
        assert result == "${NONEXISTENT_KEY}"

    def test_resolve_in_dict(self):
        with patch.dict(os.environ, {"MY_KEY": "resolved"}):
            result = _resolve_env_vars({"key": "${MY_KEY}", "other": "plain"})
            assert result["key"] == "resolved"
            assert result["other"] == "plain"

    def test_resolve_in_list(self):
        with patch.dict(os.environ, {"MY_KEY": "resolved"}):
            result = _resolve_env_vars(["${MY_KEY}", "plain"])
            assert result[0] == "resolved"
            assert result[1] == "plain"

    def test_non_env_string(self):
        result = _resolve_env_vars("just a string")
        assert result == "just a string"


class TestGetApiKey:
    def test_from_env(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-123"}):
            with patch("orchestify.core.global_config.load_global_config",
                       return_value={"api_keys": {"anthropic": "${ANTHROPIC_API_KEY}"}}):
                key = get_api_key("anthropic")
                assert key == "sk-test-123"

    def test_from_config(self):
        with patch("orchestify.core.global_config.load_global_config",
                   return_value={"api_keys": {"anthropic": "direct-key"}}):
            key = get_api_key("anthropic")
            assert key == "direct-key"

    def test_none_when_not_found(self):
        os.environ.pop("MISSING_API_KEY", None)
        with patch("orchestify.core.global_config.load_global_config",
                   return_value={"api_keys": {}}):
            key = get_api_key("missing")
            assert key is None
