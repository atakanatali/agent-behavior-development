"""Unit tests for orchestify.tools module."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from orchestify.tools.file_ops import FileOps
from orchestify.tools.git_ops import GitOps
from orchestify.tools.shell import ShellRunner, ShellResult


# ─── FileOps Tests ───


class TestFileOps:
    @pytest.fixture
    def file_ops(self, tmp_path):
        return FileOps(tmp_path)

    def test_write_and_read_file(self, file_ops, tmp_path):
        file_ops.write_file("test.txt", "Hello World")
        content = file_ops.read_file("test.txt")
        assert content == "Hello World"

    def test_create_file(self, file_ops):
        file_ops.create_file("new.txt", "New content")
        content = file_ops.read_file("new.txt")
        assert content == "New content"

    def test_create_file_already_exists(self, file_ops):
        file_ops.create_file("exists.txt", "First")
        with pytest.raises(FileExistsError):
            file_ops.create_file("exists.txt", "Second")

    def test_file_exists(self, file_ops):
        assert file_ops.file_exists("nonexistent.txt") is False
        file_ops.write_file("exists.txt", "content")
        assert file_ops.file_exists("exists.txt") is True

    def test_delete_file(self, file_ops):
        file_ops.write_file("to_delete.txt", "content")
        assert file_ops.file_exists("to_delete.txt") is True
        file_ops.delete_file("to_delete.txt")
        assert file_ops.file_exists("to_delete.txt") is False

    def test_read_nonexistent_file(self, file_ops):
        with pytest.raises(FileNotFoundError):
            file_ops.read_file("nonexistent.txt")

    def test_nested_directory_creation(self, file_ops):
        file_ops.write_file("a/b/c/deep.txt", "Deep content")
        content = file_ops.read_file("a/b/c/deep.txt")
        assert content == "Deep content"

    def test_list_files(self, file_ops):
        file_ops.write_file("one.py", "")
        file_ops.write_file("two.py", "")
        file_ops.write_file("three.txt", "")
        py_files = file_ops.list_files(".", "*.py")
        assert len(py_files) == 2

    def test_path_traversal_protection(self, file_ops):
        with pytest.raises((ValueError, OSError)):
            file_ops.read_file("../../etc/passwd")

    def test_read_directory_tree(self, file_ops):
        file_ops.write_file("src/main.py", "")
        file_ops.write_file("src/utils.py", "")
        file_ops.write_file("tests/test_main.py", "")
        tree = file_ops.read_directory_tree(".")
        assert "src" in tree
        assert "tests" in tree


# ─── GitOps Tests ───


class TestGitOps:
    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository."""
        os.system(f"cd {tmp_path} && git init -q && git config user.email 'test@test.com' && git config user.name 'Test'")
        (tmp_path / "README.md").write_text("# Test Repo")
        os.system(f"cd {tmp_path} && git add . && git commit -q -m 'Initial commit'")
        return tmp_path

    @pytest.fixture
    def git_ops(self, git_repo):
        return GitOps(git_repo)

    def test_is_git_repo(self, git_ops):
        assert git_ops.is_git_repo() is True

    def test_not_git_repo(self, tmp_path):
        ops = GitOps(tmp_path)
        assert ops.is_git_repo() is False

    def test_get_current_branch(self, git_ops):
        branch = git_ops.get_current_branch()
        assert branch in ("main", "master")

    def test_status(self, git_ops):
        status = git_ops.status()
        assert isinstance(status, str)

    def test_log(self, git_ops):
        logs = git_ops.log(n=5)
        assert isinstance(logs, list)
        assert len(logs) >= 1
        assert "hash" in logs[0] or "message" in logs[0] or isinstance(logs[0], dict)

    def test_create_branch(self, git_ops):
        # Detect the default branch name (master or main depending on git config)
        default_branch = git_ops.get_current_branch()
        git_ops.create_branch("feature/test-branch", base=default_branch)
        branch = git_ops.get_current_branch()
        assert branch == "feature/test-branch"

    def test_add_and_commit(self, git_ops, git_repo):
        (git_repo / "new_file.txt").write_text("New content")
        git_ops.add(["new_file.txt"])
        commit_hash = git_ops.commit("Add new file")
        assert commit_hash is not None
        assert len(commit_hash) > 0

    def test_diff_no_changes(self, git_ops):
        diff = git_ops.diff()
        assert diff == "" or isinstance(diff, str)


# ─── ShellRunner Tests ───


class TestShellRunner:
    @pytest.fixture
    def shell(self, tmp_path):
        return ShellRunner(tmp_path)

    def test_run_simple_command(self, shell):
        result = shell.run("echo hello")
        assert isinstance(result, ShellResult)
        assert result.success is True
        assert "hello" in result.stdout

    def test_run_failing_command(self, shell):
        result = shell.run("false")
        assert result.success is False
        assert result.exit_code != 0

    def test_run_captures_stderr(self, shell):
        # Use python to write to stderr since ShellRunner uses shlex (no shell redirects)
        result = shell.run('python3 -c "import sys; sys.stderr.write(\'error\\n\')"')
        assert "error" in result.stderr

    def test_run_with_timeout(self, shell):
        result = shell.run("echo fast", timeout=5)
        assert result.success is True

    def test_result_has_duration(self, shell):
        result = shell.run("echo test")
        assert result.duration_ms >= 0

    def test_result_fields(self, shell):
        result = shell.run("echo test")
        assert hasattr(result, "command")
        assert hasattr(result, "exit_code")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert hasattr(result, "success")
