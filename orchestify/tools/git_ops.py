"""
Git operations tool for agents.

Provides safe git command execution within a repository.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union


class GitOps:
    """
    Git operations tool for agents.

    Provides a safe interface to git operations constrained to a repository.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize GitOps with a repository root.

        Args:
            repo_root: The root directory of the git repository.

        Raises:
            ValueError: If repo_root does not exist or is not a directory.
        """
        self.repo_root = repo_root.resolve()

        if not self.repo_root.exists():
            raise ValueError(f"Repository root does not exist: {self.repo_root}")

        if not self.repo_root.is_dir():
            raise ValueError(f"Repository root is not a directory: {self.repo_root}")

    def _run_git(self, args: List[str]) -> str:
        """
        Execute a git command in the repository.

        Args:
            args: List of git command arguments (e.g., ["status", "--porcelain"]).

        Returns:
            The stdout output of the git command.

        Raises:
            RuntimeError: If the git command fails.
        """
        cmd = ["git", "-C", str(self.repo_root)] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Git command failed: {' '.join(args)}\n"
                    f"Error: {result.stderr}"
                )

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Git command timed out: {' '.join(args)}")
        except FileNotFoundError:
            raise RuntimeError("Git is not installed or not in PATH")

    def is_git_repo(self) -> bool:
        """
        Check if the repository root is a git repository.

        Returns:
            True if it's a git repository, False otherwise.
        """
        git_dir = self.repo_root / ".git"
        return git_dir.exists()

    def get_current_branch(self) -> str:
        """
        Get the current branch name.

        Returns:
            The name of the current branch.

        Raises:
            RuntimeError: If not in a git repository or command fails.
        """
        output = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return output.strip()

    def create_branch(self, branch_name: str, base: str = "main") -> None:
        """
        Create and checkout a new branch.

        Args:
            branch_name: Name for the new branch.
            base: Base branch to create from (default "main").

        Raises:
            RuntimeError: If the operation fails.
        """
        # Ensure we're on the base branch first
        self._run_git(["checkout", base])

        # Create and checkout the new branch
        self._run_git(["checkout", "-b", branch_name])

    def checkout(self, branch_name: str) -> None:
        """
        Check out a branch.

        Args:
            branch_name: Name of the branch to check out.

        Raises:
            RuntimeError: If the operation fails.
        """
        self._run_git(["checkout", branch_name])

    def add(self, files: Union[List[str], str] = ".") -> None:
        """
        Stage files for commit.

        Args:
            files: File path(s) to stage. Can be a single string or list.
                  Defaults to "." (all changes).

        Raises:
            RuntimeError: If the operation fails.
        """
        if isinstance(files, str):
            args = ["add", files]
        else:
            args = ["add"] + files

        self._run_git(args)

    def commit(self, message: str) -> str:
        """
        Create a commit with the staged changes.

        Args:
            message: The commit message.

        Returns:
            The commit hash of the new commit.

        Raises:
            RuntimeError: If the operation fails.
        """
        self._run_git(["commit", "-m", message])

        # Get the commit hash
        commit_hash = self._run_git(["rev-parse", "HEAD"])
        return commit_hash.strip()

    def push(
        self, branch: Optional[str] = None, set_upstream: bool = True
    ) -> None:
        """
        Push commits to the remote repository.

        Args:
            branch: Branch to push. If None, pushes the current branch.
            set_upstream: If True, sets the upstream branch (default True).

        Raises:
            RuntimeError: If the operation fails.
        """
        if branch is None:
            branch = self.get_current_branch()

        args = ["push"]
        if set_upstream:
            args.append("-u")
        args.extend(["origin", branch])

        self._run_git(args)

    def pull(self, branch: str = "main") -> None:
        """
        Pull changes from the remote repository.

        Args:
            branch: Branch to pull from (default "main").

        Raises:
            RuntimeError: If the operation fails.
        """
        self._run_git(["pull", "origin", branch])

    def diff(self, staged: bool = False) -> str:
        """
        Get diff output.

        Args:
            staged: If True, shows staged changes. Otherwise shows unstaged changes.

        Returns:
            The diff output.

        Raises:
            RuntimeError: If the operation fails.
        """
        args = ["diff"]
        if staged:
            args.append("--cached")

        return self._run_git(args)

    def status(self) -> str:
        """
        Get the status of the repository.

        Returns:
            The output of git status.

        Raises:
            RuntimeError: If the operation fails.
        """
        return self._run_git(["status", "--porcelain"])

    def log(self, n: int = 10) -> List[Dict[str, str]]:
        """
        Get recent commits.

        Args:
            n: Number of commits to retrieve (default 10).

        Returns:
            List of dictionaries with keys: hash, message, author, date.

        Raises:
            RuntimeError: If the operation fails.
        """
        format_str = "%H%n%s%n%an%n%ai"
        output = self._run_git(
            ["log", f"-{n}", f"--format={format_str}", "--no-merges"]
        )

        commits = []
        lines = output.split("\n")

        for i in range(0, len(lines), 4):
            if i + 3 < len(lines):
                commits.append(
                    {
                        "hash": lines[i],
                        "message": lines[i + 1],
                        "author": lines[i + 2],
                        "date": lines[i + 3],
                    }
                )

        return commits

    def stash(self) -> None:
        """
        Stash current changes.

        Raises:
            RuntimeError: If the operation fails.
        """
        self._run_git(["stash"])

    def stash_pop(self) -> None:
        """
        Pop the last stashed changes.

        Raises:
            RuntimeError: If the operation fails.
        """
        self._run_git(["stash", "pop"])

    def get_remote_url(self) -> str:
        """
        Get the URL of the origin remote.

        Returns:
            The remote URL.

        Raises:
            RuntimeError: If the operation fails.
        """
        return self._run_git(["config", "--get", "remote.origin.url"]).strip()
