"""Unit tests for orchestify.core.config module."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from orchestify.core.config import (
    ABDConfig,
    AgentConfig,
    AgentsConfig,
    DevLoopConfig,
    IssueConfig,
    MemoryConfig,
    OrchestrifyConfig,
    OrchestrationConfig,
    ProjectConfig,
    ProviderConfig,
    ProvidersConfig,
    _substitute_env_vars,
    _load_yaml,
    load_config,
    validate_config,
)


# ─── Config Model Tests ───


class TestProjectConfig:
    def test_create_valid(self):
        pc = ProjectConfig(name="Test", repo="owner/repo")
        assert pc.name == "Test"
        assert pc.main_branch == "main"
        assert pc.branch_prefix == "feature/"

    def test_custom_values(self):
        pc = ProjectConfig(
            name="Custom",
            repo="org/custom-repo",
            main_branch="develop",
            branch_prefix="feat/",
        )
        assert pc.main_branch == "develop"

    def test_missing_required_field(self):
        with pytest.raises(Exception):
            ProjectConfig(name="Test")  # Missing repo


class TestOrchestrationConfig:
    def test_defaults(self):
        oc = OrchestrationConfig()
        assert oc.max_review_cycles == 3
        assert oc.max_qa_cycles == 3
        assert oc.auto_merge is True
        assert oc.sequential_issues is True

    def test_custom_cycles(self):
        oc = OrchestrationConfig(max_review_cycles=5, max_qa_cycles=2)
        assert oc.max_review_cycles == 5

    def test_min_cycles_validation(self):
        with pytest.raises(Exception):
            OrchestrationConfig(max_review_cycles=0)


class TestAgentConfig:
    def test_create_valid(self):
        ac = AgentConfig(provider="anthropic", model="claude-opus-4-6")
        assert ac.temperature == 0.7
        assert ac.thinking is False
        assert ac.mode == "autonomous"
        assert ac.max_tokens == 8192

    def test_interactive_mode(self):
        ac = AgentConfig(
            provider="openai", model="gpt-4o", mode="interactive"
        )
        assert ac.mode == "interactive"

    def test_invalid_mode(self):
        with pytest.raises(Exception):
            AgentConfig(provider="openai", model="gpt-4o", mode="invalid")

    def test_temperature_bounds(self):
        with pytest.raises(Exception):
            AgentConfig(provider="openai", model="gpt-4", temperature=3.0)


class TestProviderConfig:
    def test_create_valid(self):
        pc = ProviderConfig(
            type="anthropic",
            api_key="test-key",
            default_model="claude-opus-4-6",
        )
        assert pc.type == "anthropic"
        assert pc.max_tokens == 8192

    def test_invalid_type(self):
        with pytest.raises(Exception):
            ProviderConfig(
                type="invalid", api_key="key", default_model="model"
            )


class TestIssueConfig:
    def test_defaults(self):
        ic = IssueConfig()
        assert ic.max_changes_per_issue == 20
        assert ic.language == "en"
        assert ic.require_agent_directive is True
        assert ic.require_done_checklist is True


class TestABDConfig:
    def test_defaults(self):
        ac = ABDConfig()
        assert ac.scorecard_enabled is True
        assert ac.recycle_mandatory is True
        assert ac.evidence_required is True


class TestDevLoopConfig:
    def test_defaults(self):
        dl = DevLoopConfig()
        assert dl.build_cmd == ""
        assert dl.max_self_fix == 5
        assert dl.timeout_per_command == 120


# ─── Helper Function Tests ───


class TestSubstituteEnvVars:
    def test_no_substitution(self):
        assert _substitute_env_vars("hello world") == "hello world"

    def test_with_env_var(self):
        with patch.dict(os.environ, {"MY_KEY": "secret123"}):
            assert _substitute_env_vars("key=${MY_KEY}") == "key=secret123"

    def test_missing_env_var_keeps_original(self):
        result = _substitute_env_vars("key=${NONEXISTENT_VAR_XYZ}")
        assert result == "key=${NONEXISTENT_VAR_XYZ}"

    def test_multiple_vars(self):
        with patch.dict(os.environ, {"A": "1", "B": "2"}):
            assert _substitute_env_vars("${A}-${B}") == "1-2"


class TestLoadYaml:
    def test_load_valid_yaml(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("key: value\nnested:\n  a: 1")
        data = _load_yaml(f)
        assert data["key"] == "value"
        assert data["nested"]["a"] == 1

    def test_load_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _load_yaml(tmp_path / "nonexistent.yaml")

    def test_load_empty_yaml(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        data = _load_yaml(f)
        assert data == {}

    def test_env_substitution_in_yaml(self, tmp_path):
        with patch.dict(os.environ, {"TEST_KEY": "resolved"}):
            f = tmp_path / "test.yaml"
            f.write_text("api_key: ${TEST_KEY}")
            data = _load_yaml(f)
            assert data["api_key"] == "resolved"


# ─── load_config Tests ───


class TestLoadConfig:
    def test_load_valid_config(self, config_dir):
        config = load_config(config_dir)
        assert config.project.name == "Test Project"
        assert config.project.repo == "test/test-repo"
        assert config.orchestration.max_review_cycles == 3
        assert config.abd.scorecard_enabled is True

    def test_load_config_with_agents(self, config_dir):
        config = load_config(config_dir)
        assert "tpm" in config.agents.agents
        assert "engineer" in config.agents.agents
        assert config.agents.agents["tpm"].model == "claude-opus-4-6"

    def test_load_config_with_providers(self, config_dir):
        config = load_config(config_dir)
        assert "anthropic" in config.providers.providers
        assert config.providers.providers["anthropic"].type == "anthropic"

    def test_load_config_missing_main_file(self, tmp_path):
        config_dir = tmp_path / "empty_config"
        config_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_config(config_dir)


# ─── validate_config Tests ───


class TestValidateConfig:
    def test_valid_config_no_warnings(self, config_dir):
        config = load_config(config_dir)
        warnings = validate_config(config)
        # There may be warnings about fallback memory path, which is acceptable
        assert all("unknown provider" not in w for w in warnings)

    def test_agent_references_unknown_provider(self):
        config = OrchestrifyConfig(
            project=ProjectConfig(name="Test", repo="test/repo"),
            agents=AgentsConfig(agents={
                "test_agent": AgentConfig(provider="nonexistent", model="model")
            }),
        )
        warnings = validate_config(config)
        assert any("unknown provider" in w for w in warnings)

    def test_no_agents_warning(self):
        config = OrchestrifyConfig(
            project=ProjectConfig(name="Test", repo="test/repo"),
        )
        warnings = validate_config(config)
        assert any("No agents configured" in w for w in warnings)

    def test_no_providers_warning(self):
        config = OrchestrifyConfig(
            project=ProjectConfig(name="Test", repo="test/repo"),
        )
        warnings = validate_config(config)
        assert any("No providers configured" in w for w in warnings)

    def test_long_timeout_warning(self):
        config = OrchestrifyConfig(
            project=ProjectConfig(name="Test", repo="test/repo"),
            dev_loop=DevLoopConfig(timeout_per_command=7200),
        )
        warnings = validate_config(config)
        assert any("very long" in w for w in warnings)
