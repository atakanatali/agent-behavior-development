"""Unit tests for orchestify.cli module."""
import pytest
from click.testing import CliRunner

from orchestify.cli.main import cli
from orchestify import __version__


class TestCLIBasics:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "orchestify" in result.output.lower() or "ABD" in result.output

    def test_no_args_shows_welcome(self, runner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        # Welcome screen should contain version
        assert __version__ in result.output or "Orchestify" in result.output

    def test_init_help(self, runner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "sprint" in result.output.lower() or "git" in result.output.lower()

    def test_plan_help(self, runner):
        result = runner.invoke(cli, ["plan", "--help"])
        assert result.exit_code == 0
        assert "TPM" in result.output or "plan" in result.output.lower()

    def test_start_help(self, runner):
        result = runner.invoke(cli, ["start", "--help"])
        assert result.exit_code == 0
        assert "pipeline" in result.output.lower() or "run" in result.output.lower()

    def test_status_help(self, runner):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_inspect_help(self, runner):
        result = runner.invoke(cli, ["inspect", "--help"])
        assert result.exit_code == 0
        assert "agent" in result.output.lower()

    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    def test_stop_help(self, runner):
        result = runner.invoke(cli, ["stop", "--help"])
        assert result.exit_code == 0

    def test_resume_help(self, runner):
        result = runner.invoke(cli, ["resume", "--help"])
        assert result.exit_code == 0

    def test_install_help(self, runner):
        result = runner.invoke(cli, ["install", "--help"])
        assert result.exit_code == 0


class TestCLICommands:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_init_no_git(self, runner, tmp_path):
        """init should fail without git repo (when not in any git tree)."""
        # Create a dir guaranteed not to be inside any git repo
        isolated = tmp_path / "no_git_here"
        isolated.mkdir()
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(isolated)
            result = runner.invoke(cli, ["init"])
            # Either fails (exit 1) or shows error message
            assert result.exit_code != 0 or "not a git" in result.output.lower() or "error" in result.output.lower()
        finally:
            os.chdir(old_cwd)

    def test_init_with_no_git_check(self, runner, tmp_path):
        """init should work with --no-git-check."""
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["init", "--no-git-check"])
            assert result.exit_code == 0
            assert "sprint" in result.output.lower() or "initialized" in result.output.lower()
        finally:
            os.chdir(old_cwd)

    def test_status_no_config(self, runner, tmp_path):
        """status should handle missing config gracefully."""
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["status"])
            # Should either show no config message or exit without crash
            assert result.exit_code == 0 or "not found" in result.output.lower() or "init" in result.output.lower()
        finally:
            os.chdir(old_cwd)

    def test_config_validate_no_config(self, runner, tmp_path):
        """config validate without config should fail gracefully."""
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["config", "validate"])
            assert result.exit_code != 0 or "not found" in result.output.lower() or "error" in result.output.lower()
        finally:
            os.chdir(old_cwd)

    def test_start_dry_run_no_config(self, runner, tmp_path):
        """start --dry-run without config should fail gracefully."""
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["start", "--dry-run"])
            assert result.exit_code != 0 or "not found" in result.output.lower() or "error" in result.output.lower()
        finally:
            os.chdir(old_cwd)
